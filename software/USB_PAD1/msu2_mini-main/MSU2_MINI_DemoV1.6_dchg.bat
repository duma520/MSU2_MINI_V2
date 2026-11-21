@echo off
cd /D "%~dp0"
set "BASEDIR=%cd%"

::python.exe %BASEDIR%\MSU2_MINI_DemoV1.6_dchg.py
powershell Start-Process "python.exe %BASEDIR%\MSU2_MINI_DemoV1.6_dchg.py" -Verb runAs
if not "%errorlevel%" == "0" (
    echo "An error occurred!"
    pause
)
