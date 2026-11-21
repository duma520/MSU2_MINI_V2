@echo off
cd /D "%~dp0"

setlocal enabledelayedexpansion

for /f "delims=" %%i in ('where pyinstaller') do (
    set "pypath=%%~dpi"
)
set "dllpath=%pypath%..\Lib\site-packages\HardwareMonitor\lib\*.dll"

:: -F one file
:: -D one dir
:: -w no console
pyinstaller -D -y --clean --distpath=dist ^
    --add-data "resource;resource" ^
    --add-binary="%dllpath%;HardwareMonitor\lib" ^
    --icon "resource/icon.ico" ^
    -n MSU2_MINI_DemoV1.6 MSU2_MINI_DemoV1.6_dchg.py

endlocal

copy /Y MSU2_MINI.json dist\MSU2_MINI_DemoV1.6
rmdir /S /Q .\build\
pause
