# clipsync

局域网剪贴板同步，支持**文本和图片**。

两台机器，一台当服务端，一台当客户端。连上以后双向同步——你在这台复制什么，对面马上就有。

## 为什么自己写

[natclip](https://github.com/dodobyte/natclip) 只能同步文本，图片不行。

SyncClipboard 功能全，但要装客户端、配服务器、有账号体系。

这个就一个文件、不到三百行，两边跑同一份，不需要装额外的软件。

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

只在你自己家的网络里工作，换到别的网络会自动停（见下面「只在家里的网络里工作」）。

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

## 只在家里的网络里工作

脚本开头有两个常量，改成你自己家的：

```python
HOME_NET = "192.168.1."              # 家里的网段
ROUTER_MAC = "1c:67:4a:ab:90:76"     # 家里路由器的 MAC
```

**两道检查都要过，少一道都不干活：**

1. 本机在 `HOME_NET` 网段里
2. 路由器那个 IP 在 ARP 表里的 MAC 就是 `ROUTER_MAC`

只查网段是不够的。很多公共 Wi-Fi 也用 `192.168.1.x`，网段检查会误判成在家。路由器 MAC 是硬件地址，撞不上。

服务端不在家就**不监听端口**，客户端不在家就**不往外连**。回到家一分钟内自动恢复开始同步。所以笔记本带出门不用手动关。

路由器 MAC 这么查：

```sh
# macOS
arp -n 192.168.1.1

# Windows
arp -a 192.168.1.1
```

输出里的那一串十六进制就是，例如 `1c:67:4a:ab:90:76`。

**判断本机 IP 不要用探测 `8.8.8.8` 的办法。** 开了 Clash TUN 之类的隧道时会被劫持，拿到的是 `198.18.0.1` 这种假地址。探测路由器地址（`192.168.1.1`）才对，本地子网会绕过隧道。

## 安全

**明文传输，没有加密。**

任何能连上 48021 端口的人都能看到你的剪贴板内容，也能往里写。

你复制的**密码、验证码、token 都会明文经过局域网**。

「只在家里的网络里工作」解决的是**笔记本带出门**的情况。它挡不住同一个家里的网络里的其他人——那个场景下仍然是明文，谁都能看。

只在你自己信的局域网里用。

## 已知限制

- 只同步文本和图片，**不同步文件**
- 没有剪贴板历史
- 一个服务端同时只服务一个客户端
- macOS 上每次轮询要起一个 `osascript` 进程，约 29 毫秒。0.5 秒轮询一次，大概占单核 6%。笔记本上想省电可以调大 `POLL`

## 许可

MIT
