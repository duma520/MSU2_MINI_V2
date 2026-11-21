@echo off
cd /D "%~dp0"
set "BASEDIR=%cd%"

python.exe %BASEDIR%\MSU2_MINI_MG.py
if not "%errorlevel%" == "0" (
    echo "An error occurred!"
    pause
)
