@echo off
chcp 1251 >nul
echo.
echo ====================================================
echo =                   HH Parser                      =
echo ====================================================
echo.

echo.
echo Installing dependencies...
pip install sv-ttk
pip install playwright
pip install openpyxl
pip install pandas

echo.
echo Installing Playwright browser...
playwright install chromium

echo.
echo Compiling EXE...
pyinstaller --clean --noconfirm ^
--distpath=. ^
--name="HHParser" ^
--onedir ^
--windowed ^
--icon="static/HHParse_logo.ico" ^
--add-data="static;static" ^
--add-data="%LOCALAPPDATA%\ms-playwright\chromium-1200;ms-playwright\chromium-1200" ^
--runtime-hook=playwright_runtime_hook.py ^
gui.py

echo.
echo Moving files...
if exist "HHParser" (
    move "HHParser\HHParser.exe" "." >nul 2>nul
    if exist "HHParser\_internal" (
        move "HHParser\_internal" "." >nul 2>nul
    )
    for %%F in ("HHParser\*.*") do (
        if not "%%F"=="HHParser\_internal" if not "%%F"=="HHParser\HHParser.exe" (
            move "%%F" "." >nul 2>nul
        )
    )
    rmdir /s /q "HHParser" 2>nul
    rmdir /s /q build 2>nul
    del *.spec 2>nul
)

echo.
echo Creating directories...
if not exist "hh_parse_results" mkdir "hh_parse_results"
if not exist "static" mkdir "static"

echo.
echo Creating desktop shortcut...
set "EXE_PATH=%CD%\HHParser.exe"
set "DESKTOP_PATH=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=HHParser.lnk"
set "ICON_PATH=%CD%\static\HHParse_logo.ico"

if not exist "%EXE_PATH%" (
    if exist "dist\HHParser.exe" (
        move "dist\HHParser.exe" "." >nul 2>nul
    ) else (
        echo ERROR: Cannot find HHParser.exe
        pause
        exit /b 1
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\%SHORTCUT_NAME%'); ^
$Shortcut.TargetPath = '%EXE_PATH%'; ^
$Shortcut.WorkingDirectory = '%CD%'; ^
if (Test-Path '%ICON_PATH%') { ^
    $Shortcut.IconLocation = '%ICON_PATH%'; ^
} ^
$Shortcut.Save();"

if exist "%DESKTOP_PATH%\%SHORTCUT_NAME%" (
    echo Desktop shortcut created: %SHORTCUT_NAME%
) else (
    echo WARNING: Failed to create desktop shortcut
)

echo.
echo ====================================================
echo Installation completed!
echo.
echo Launch HHParser from desktop shortcut or HHParser.exe
echo ====================================================
echo.
pause