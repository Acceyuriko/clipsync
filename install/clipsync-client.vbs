' clipsync client: connect to the server and keep the clipboard in sync.
'
' Install: drop this file into
'   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
' and fix the two paths and the server IP below.
'
' Window mode 0 keeps it hidden; output goes to clipsync.log.

Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c C:\Users\zec_i\AppData\Local\Microsoft\WindowsApps\python.exe C:\Users\zec_i\bin\clipsync.py connect 192.168.1.181 > C:\Users\zec_i\bin\clipsync.log 2>&1", 0, False
