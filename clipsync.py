#!/usr/bin/env python3
"""局域网剪贴板同步，支持文本和图片。

服务端:  python3 clipsync.py serve
客户端:  python  clipsync.py connect 192.168.1.181

服务端监听 48021，客户端连上去。连接建立后两边双向同步。
"""
import base64
import hashlib
import io
import json
import socket
import struct
import subprocess
import sys
import time

PORT = 48021
POLL = 0.5

# ---------------------------------------------------------------- macOS

MAC_IMG = "/tmp/clipsync-mac.png"
MAC_IN = "/tmp/clipsync-mac.in"

JXA_READ = """
ObjC.import("AppKit");
var pb = $.NSPasteboard.generalPasteboard;
var d = pb.dataForType("public.png");
if (!d || d.isNil()) {
    var t = pb.dataForType("public.tiff");
    if (t && !t.isNil()) {
        var rep = $.NSBitmapImageRep.imageRepWithData(t);
        d = rep.representationUsingTypeProperties($.NSPNGFileType, $());
    }
}
if (d && !d.isNil()) {
    d.writeToFileAtomically("%s", true);
    "IMAGE";
} else {
    var s = pb.stringForType("public.utf8-plain-text");
    "TEXT" + (s && !s.isNil() ? s.js : "");
}
""" % MAC_IMG

JXA_WRITE = """
function run(argv) {
    ObjC.import("AppKit");
    ObjC.import("Foundation");
    var pb = $.NSPasteboard.generalPasteboard;
    if (argv[0] == "image") {
        var d = $.NSData.dataWithContentsOfFile(argv[1]);
        pb.clearContents;
        pb.setDataForType(d, "public.png");
    } else {
        var s = $.NSString.stringWithContentsOfFileEncodingError(argv[1], $.NSUTF8StringEncoding, null);
        pb.clearContents;
        pb.setStringForType(s, "public.utf8-plain-text");
    }
    "OK";
}
"""


def _mac_read():
    out = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", JXA_READ],
        capture_output=True, text=True).stdout
    if out.endswith("\n"):
        out = out[:-1]
    if out == "IMAGE":
        with open(MAC_IMG, "rb") as f:
            return "image", f.read()
    return "text", out[4:].encode()


def _mac_write(kind, data):
    with open(MAC_IN, "wb") as f:
        f.write(data)
    subprocess.run(["osascript", "-l", "JavaScript", "-e", JXA_WRITE, kind, MAC_IN],
                   capture_output=True)


# -------------------------------------------------------------- Windows

def _win_open():
    import win32clipboard
    for _ in range(40):
        try:
            win32clipboard.OpenClipboard()
            return win32clipboard
        except Exception:
            time.sleep(0.05)
    raise RuntimeError("剪贴板被别的程序占着")


def _win_read():
    from PIL import Image, ImageGrab
    img = ImageGrab.grabclipboard()
    if isinstance(img, Image.Image):
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return "image", buf.getvalue()
    cb = _win_open()
    try:
        text = cb.GetClipboardData(cb.CF_UNICODETEXT)
    except Exception:
        text = ""
    finally:
        cb.CloseClipboard()
    return "text", text.encode()


def _win_write(kind, data):
    cb = _win_open()
    try:
        cb.EmptyClipboard()
        if kind == "image":
            from PIL import Image
            buf = io.BytesIO()
            Image.open(io.BytesIO(data)).convert("RGB").save(buf, "BMP")
            cb.SetClipboardData(cb.CF_DIB, buf.getvalue()[14:])
        else:
            cb.SetClipboardData(cb.CF_UNICODETEXT, data.decode())
    finally:
        cb.CloseClipboard()


if sys.platform == "darwin":
    read_clip, write_clip = _mac_read, _mac_write
else:
    read_clip, write_clip = _win_read, _win_write

# -------------------------------------------------------------- 同步逻辑


def send_msg(conn, obj):
    raw = json.dumps(obj).encode()
    conn.sendall(struct.pack(">I", len(raw)) + raw)


def _recvall(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("对端断开")
        buf += chunk
    return buf


def recv_msg(conn):
    n = struct.unpack(">I", _recvall(conn, 4))[0]
    return json.loads(_recvall(conn, n))


def session(conn):
    kind, data = read_clip()
    hash_ = hashlib.md5(data).hexdigest()
    my_ts = time.time()
    sent = None
    while True:
        nkind, ndata = read_clip()
        nhash = hashlib.md5(ndata).hexdigest()
        now = time.time()
        if nhash != hash_:
            kind, data, hash_ = nkind, ndata, nhash
            my_ts = now

        send_msg(conn, {
            "hash": hash_,
            "kind": kind,
            "ts": my_ts,
            "sys_time": now,
            "data": base64.b64encode(data).decode() if hash_ != sent else None,
        })
        sent = hash_

        msg = recv_msg(conn)
        rts = msg["ts"] + (time.time() - msg["sys_time"])
        if msg["data"] is not None and msg["hash"] != hash_ and rts > my_ts:
            kind = msg["kind"]
            data = base64.b64decode(msg["data"])
            hash_ = msg["hash"]
            my_ts = rts
            sent = hash_
            write_clip(kind, data)

        time.sleep(POLL)


def serve():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(1)
    print("监听 %d，等客户端连上来" % PORT, flush=True)
    while True:
        conn, addr = srv.accept()
        print("已连接 %s" % addr[0], flush=True)
        try:
            session(conn)
        except Exception as e:
            print("断开: %s" % e, flush=True)
        conn.close()


def connect(host):
    while True:
        try:
            conn = socket.create_connection((host, PORT))
            print("已连上 %s" % host, flush=True)
            session(conn)
        except Exception as e:
            print("连不上(%s)，2 秒后重试" % e, flush=True)
            time.sleep(2)


if __name__ == "__main__":
    if sys.argv[1] == "serve":
        serve()
    else:
        connect(sys.argv[2])
