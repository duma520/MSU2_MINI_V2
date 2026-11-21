@echo off
cd /D "%~dp0"

set "mainfilename=MSU2_MINI_DemoV1.6_dchg"
rem mkdir %mainfilename%.dist 2>nul

set "datenow=%date:~5,2%%date:~8,2%"
set "outfilename=MSU2_MINI_MG(by nuitka)-%datenow%.exe"
move /y "%outfilename%" "%outfilename%.bak" 2>nul 1>nul

setlocal enabledelayedexpansion
for /f "delims=" %%i in ('where pyinstaller') do (
    set "pypath=%%~dpi"
)

rem --lto=yes
rem --standalone
rem --onefile
rem --windows-console-mode=disable
python -m nuitka --onefile --clean-cache=all --windows-console-mode=disable ^
	--enable-plugin=tk-inter --remove-output ^
	--include-data-files="%~dp0/resource/*"="resource/" ^
	--include-data-files="%pypath%../Lib/site-packages/HardwareMonitor/lib/*.dll"="HardwareMonitor/lib/" ^
	--windows-icon-from-ico=resource/icon.ico ^
	--output-filename="%outfilename%" ^
	%mainfilename%.py

endlocal

::move /Y MSU2_mini.exe "%outfilename%"

pause
