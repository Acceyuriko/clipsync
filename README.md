# clipsync

局域网剪贴板同步，支持**文本和图片**。

两台机器，一台当服务端，一台当客户端。连上以后双向同步——你在这台复制什么，对面马上就有。

## 为什么自己写

[natclip](https://github.com/dodobyte/natclip) 只能同步文本，图片不行。

SyncClipboard 功能全，但要装客户端、配服务器、有账号体系。

这个就一个文件、两百多行，两边跑同一份，不需要装额外的软件。

## 要求

- Python 3

| 系统 | 要装什么 |
|---|---|
| Windows | `pip install pillow pywin32` |
| macOS | **什么都不用装** |

macOS 上不装东西是有意的。系统自带的 Python 是 3.9，pip 太老，装不了 pyobjc。所以这里改用 macOS 自带的 JXA，通过 `osascript` 直接读剪贴板，一个依赖都不引入。

## 用法

**服务端**（IP 固定的那台）：

```sh
python3 clipsync.py serve
```

**客户端**（另一台）：

```sh
python clipsync.py connect 192.168.1.181
```

把 `192.168.1.181` 换成服务端的 IP。

连不上会每 2 秒重试，断了会自动重连，不用管。

## 装成开机自启

`install/` 目录里有两个现成的文件。

### macOS

1. 把脚本放到 `~/bin/clipsync.py`
2. 把 `install/com.clipsync.server.plist` 里的路径改成你的，放到 `~/Library/LaunchAgents/`
3. 注册：

```sh
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.clipsync.server.plist
```

日志在 `~/Library/Logs/clipsync.log`。

### Windows

把 `install/clipsync-client.vbs` 里的路径和 IP 改对，丢进启动文件夹：

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

它用 `cmd /c ... > clipsync.log` 启动，窗口是隐藏的，日志写到 `clipsync.log`。

## 怎么工作

每 0.5 秒看一眼自己的剪贴板。内容变了（比 MD5）就发给对面。

对面收到后**比时间戳，谁新听谁的**。时间戳带时钟偏差校正，两台机器时间不用对准。

这套规则解决了一个具体问题：两边同时启动时，不会互相把对方的剪贴板覆盖掉。

## 图片是怎么处理的

系统 | 读 | 写
---|---|---
macOS | `NSPasteboard.dataForType("public.png")`。没有 PNG 就取 `public.tiff`，用 `NSBitmapImageRep` 转成 PNG。 | `NSPasteboard.setDataForType(data, "public.png")`
Windows | `PIL.ImageGrab.grabclipboard()` | 转成 BMP，砍掉前 14 字节文件头，写进 `CF_DIB`

TIFF 回退是必须的——很多 macOS 程序复制图片时只往剪贴板放 TIFF，不放 PNG。

## 安全

**明文传输，没有加密。**

任何能连上 48021 端口的人都能看到你的剪贴板内容，也能往里写。

你复制的**密码、验证码、token 都会明文经过局域网**。

只在你自己信的局域网里用。

## 已知限制

- 只同步文本和图片，**不同步文件**
- 没有剪贴板历史
- 一个服务端同时只服务一个客户端
- macOS 上每次轮询要起一个 `osascript` 进程，约 29 毫秒。0.5 秒轮询一次，大概占单核 6%。笔记本上想省电可以调大 `POLL`

## 许可

MIT
