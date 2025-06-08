@echo off
setlocal enabledelayedexpansion

REM Get the name of this script
set "self=%~nx0"

REM Loop through all .bat files in the current directory
for %%f in (*.bat) do (
    if /I not "%%~nxf"=="%self%" (
        del "%%~f" >nul 2>&1
    )
)

REM Exit script
exit
