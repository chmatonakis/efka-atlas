@echo off
echo Installing Ghostscript for Windows...
echo.

REM Create temp directory
if not exist "temp" mkdir temp
cd temp

echo Downloading Ghostscript...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs1003/gs1003w64.exe' -OutFile 'gs1003w64.exe'"

echo.
echo Installing Ghostscript...
gs1003w64.exe /S

echo.
echo Adding Ghostscript to PATH...
setx PATH "%PATH%;C:\Program Files\gs\gs10.03.0\bin" /M

echo.
echo Ghostscript installation completed!
echo Please restart your command prompt and try running the app again.
echo.
pause


