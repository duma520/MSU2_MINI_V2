@echo off
REM ============================================================
REM  USB副屏工具 MSU2_MINI_V2  Nuitka 编译脚本
REM  使用前请先安装: pip install nuitka ordered-set zstandard
REM  建议在 PowerShell 中执行此脚本
REM ============================================================

nuitka --standalone ^
    --enable-plugin=tk-inter ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=resource\icon.ico ^
    --include-data-dir=resource=resource ^
    --include-package=serial ^
    --include-package=cv2 ^
    --include-package=PIL ^
    --include-package=numpy ^
    --include-package=psutil ^
    --include-package=pystray ^
    --include-package=win32gui ^
    --include-package=win32ui ^
    --include-package=win32con ^
    --include-package=win32process ^
    --include-package=mss ^
    --include-package=PyCameraList ^
    --follow-imports ^
    --jobs=4 ^
    --output-dir=build_output ^
    MSU2_MINI_V2.py

echo.
echo 编译完成！输出目录: build_output\MSU2_MINI_V2.dist\
pause
