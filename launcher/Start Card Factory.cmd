@echo off
rem Starts Card Factory without a console window (spec RN-27, RN-40).
if not exist "%~dp0python\pythonw.exe" goto missing
if not exist "%~dp0launcher\start.pyw" goto missing
start "" "%~dp0python\pythonw.exe" "%~dp0launcher\start.pyw"
exit /b 0

:missing
echo.
echo Card Factory cannot start from here.
echo The python and launcher folders were not found next to this file:
echo "%~dp0"
echo.
echo How to fix: extract the whole zip first (right-click the zip, then
echo Extract All), open the extracted folder and double-click
echo "Start Card Factory.cmd" there.
echo.
pause
exit /b 1
