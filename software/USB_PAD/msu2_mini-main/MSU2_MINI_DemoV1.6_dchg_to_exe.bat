@echo off
cd /D "%~dp0"

set "datenow=%date:~5,2%%date:~8,2%"
set "outfilename=MSU2_MINI_MG(by pyinstaller)-%datenow%.exe"
move /y "%outfilename%" "%outfilename%.bak" 2>nul 1>nul

setlocal enabledelayedexpansion

for /f "delims=" %%i in ('where pyinstaller') do (
    set "pypath=%%~dpi"
)
set "dllpath=%pypath%..\Lib\site-packages\HardwareMonitor\lib\*.dll"

:: -F one file
:: -D one dir
:: -w no console
pyinstaller -F -w -y --clean --distpath=dist ^
    --add-data "resource;resource" ^
    --add-binary="%dllpath%;HardwareMonitor\lib" ^
    --icon "resource/icon.ico" ^
    -n "%outfilename%" MSU2_MINI_DemoV1.6_dchg.py

endlocal

move /Y "dist\%outfilename%" .
rmdir /S /Q .\dist\ .\build\
del /Q "%outfilename%.spec"
pause
