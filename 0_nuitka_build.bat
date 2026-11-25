@echo off
REM 本脚本含中文注释/参数，先切到 UTF-8 代码页（退出前恢复原代码页）
for /f "tokens=2 delims=:" %%a in ('chcp') do set OLDCP=%%a
chcp 65001 >nul

REM ============================================================
REM  USB Sub-Screen Tool MSU2_MINI_V2 (PySide6 / Qt)  Nuitka build script
REM  Main file: MSU2_MINI_V2.py  (PySide6 UI; Tkinter backup: MSU2_MINI_V2_tk.py)
REM  Before use, install: pip install nuitka ordered-set zstandard PySide6
REM  Optional API protocols (auto-skip if missing):
REM    grpcio (gRPC, v5.9.0)  paho-mqtt (MQTT, v5.10.0)  pyzmq (ZeroMQ)
REM  Optional system-monitor deps (v5.12.0, auto-skip if missing):
REM    pynvml (NVIDIA GPU)  wmi (CPU temp)  -- 本机需已安装才会打包
REM  Output: build_output\MSU2_MINI_V2.dist\
REM          ★ 发布时必须整体拷贝该目录（exe 依赖同目录的 python310.dll、PySide6、
REM            LibreHardwareMonitor、resource 等），单独拷贝 exe 无法运行。
REM ============================================================

REM 必须以本脚本所在目录为工作目录（resource\icon.ico、device_protocol.json 均按相对路径打包）
cd /d "%~dp0"

REM 主程序版本号（必须与 MSU2_MINI_V2.py 的 PROGRAM_VERSION 保持一致）
set APP_VER=5.40.0
REM 控制台模式：
REM   disable = 正式发布，无控制台（print 输出进 NUL，看不到）
REM   attach  = 从 cmd/powershell 运行 exe 时能看到日志，双击运行仍无控制台窗口
REM             （排查"编译后才有、源码运行没有"的问题时改成 attach 再编译）
set CONSOLE_MODE=disable
REM 是否把本机设置同步进发布目录：1=同步 config\*.json，0=不同步
REM   同步后换目录/换电脑运行 exe 仍沿用本机配置，不会"像重置了一样"
REM   ★ .env 永远不参与同步：它含 API 密钥，随包分发等于把密钥公开。
REM     发布时请改用 .env.example，让使用者自己填。
set SYNC_CONFIG=1

if not exist "MSU2_MINI_V2.py" (
    echo [错误] 未找到 MSU2_MINI_V2.py，请在项目目录运行本脚本。
    chcp%OLDCP% >nul
    pause
    exit /b 1
)

echo 正在编译（版本 %APP_VER%，控制台模式 %CONSOLE_MODE%）...
echo.

REM ★ 必须用 call 调用：本机的 nuitka 是 nuitka.cmd（批处理），
REM   不加 call 时当前脚本会在 nuitka 处被"接管"并终止，后面的后处理/提示都不会执行。
call nuitka --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=%CONSOLE_MODE% ^
    --windows-icon-from-ico=resource\icon.ico ^
    --company-name="杜玛" ^
    --product-name="USB副屏工具" ^
    --file-description="USB副屏工具 MSU2_MINI_V2" ^
    --file-version=%APP_VER% ^
    --product-version=%APP_VER% ^
    --include-data-dir=resource=resource ^
    --include-data-files=device_protocol.json=device_protocol.json ^
    --include-data-dir=LibreHardwareMonitor=LibreHardwareMonitor ^
    --include-data-dir=LibreHardwareMonitor.NET.10=LibreHardwareMonitor.NET.10 ^
    --include-package=HardwareMonitor ^
    --include-package=serial ^
    --include-package=cv2 ^
    --include-package=PIL ^
    --include-package=numpy ^
    --include-package=psutil ^
    --include-package=pynvml ^
    --include-package=wmi ^
    --include-package=pystray ^
    --include-package=win32gui ^
    --include-package=win32ui ^
    --include-package=win32con ^
    --include-package=win32process ^
    --include-package=mss ^
    --include-package=PyCameraList ^
    --include-package=winsdk ^
    --include-package=PySide6 ^
    --include-package=zmq ^
    --include-package=grpc ^
    --include-package=google.protobuf ^
    --include-package=paho ^
    --follow-imports ^
    --jobs=4 ^
    --assume-yes-for-downloads ^
    --remove-output ^
    --output-dir=build_output ^
    MSU2_MINI_V2.py

if errorlevel 1 (
    echo.
    echo [失败] 编译出错，请查看上面的 Nuitka 输出。
    chcp%OLDCP% >nul
    pause
    exit /b 1
)

REM ---------- 编译后：把发布目录整理成"可整体拷走"的目录 ----------
set DIST=build_output\MSU2_MINI_V2.dist
if not exist "%DIST%\MSU2_MINI_V2.exe" if exist "build_output\MSU2_MINI_V2\MSU2_MINI_V2.exe" set DIST=build_output\MSU2_MINI_V2

if not exist "%DIST%\MSU2_MINI_V2.exe" (
    echo [提示] 未找到发布目录 %DIST%\MSU2_MINI_V2.exe
    chcp%OLDCP% >nul
    pause
    exit /b 1
)

if not exist "%DIST%\hotfolder" mkdir "%DIST%\hotfolder"

if "%SYNC_CONFIG%"=="1" (
    if not exist "%DIST%\config" mkdir "%DIST%\config"
    if exist "config\*.json" xcopy "config\*.json" "%DIST%\config\" /D /Y >nul
    echo 已同步本机设置到发布目录: config（不含 .env）
    if exist "%DIST%\.env" (
        del /f /q "%DIST%\.env" 2>nul
        echo [警告] 发布目录里发现 .env，已删除（内含 API 密钥，禁止分发）
    )
)

echo.
echo Build finished! Output: %DIST%\
echo.
echo 发布方法：把整个 "%DIST%" 目录拷贝到目标机器后再运行里面的 MSU2_MINI_V2.exe；
echo           只拷 exe 会缺少 python310.dll / PySide6 / LibreHardwareMonitor / resource，无法运行。
echo 设置位置：exe 同目录的 config 子目录（每屏 MSU2_MINI_^<SN^>.json、电视墙、界面状态）；
echo           使用者需自己在 exe 同目录放 .env 填 API 密钥（参考 .env.example）。
echo           config 可以随包带走，.env 绝对不能放进发布包。
echo.
chcp%OLDCP% >nul
pause
