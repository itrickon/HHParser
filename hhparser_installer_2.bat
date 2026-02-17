@echo off
chcp 1251 >nul
cd /d "%~dp0"

echo.
echo ====================================================
echo =                   HH Parser                      =
echo ====================================================
echo.

echo.
echo Installing dependencies globally...
pip install sv-ttk
pip install pyinstaller
pip install pandas
pip install openpyxl
pip install playwright

:: Проверяем наличие tkinter
echo.
echo Checking for tkinter...
python -c "import tkinter" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: tkinter not found! It should be included with Python.
    echo.
)
:: Устанавливаем браузеры Playwright в системную папку
echo.

set "PLAYWRIGHT_BROWSERS_PATH=C:\Program Files\ms-playwright"
setx PLAYWRIGHT_BROWSERS_PATH "C:\Program Files\ms-playwright" /M

:: Создаем папку если её нет
if not exist "C:\Program Files\ms-playwright" (
    mkdir "C:\Program Files\ms-playwright"
)

:: Устанавливаем браузеры в указанную папку
echo Installing Chromium...
python -m playwright install chromium --force

echo.
echo Compiling HHParser EXE...

:: Находим путь к Python
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.prefix)"') do set PYTHON_PREFIX=%%i

echo Python path: %PYTHON_PATH%
echo Python prefix: %PYTHON_PREFIX%

:: Компиляция в один EXE
pyinstaller --clean --noconfirm ^
    --distpath=. ^
    --name="HHParser" ^
    --onefile ^
    --windowed ^
    --icon="static/HHParse_logo.ico" ^
    --add-data="static;static" ^
    --paths="%PYTHON_PREFIX%\Lib" ^
    --paths="%PYTHON_PREFIX%\Lib\tkinter" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.filedialog ^
    --hidden-import=sv_ttk ^
    --hidden-import=playwright ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    gui.py

:: Проверяем создание exe
if not exist "HHParser.exe" (
    echo ERROR: HHParser.exe not found!
    echo Trying alternative compilation with --onedir...
    pyinstaller --clean --noconfirm ^
        --distpath=. ^
        --name="HHParser" ^
        --onedir ^
        --windowed ^
        --icon="static/HHParse_logo.ico" ^
        --add-data="static;static" ^
        --hidden-import=tkinter ^
        --hidden-import=sv_ttk ^
        --hidden-import=playwright ^
        --hidden-import=pandas ^
        --hidden-import=openpyxl ^
        gui.py

    if not exist "HHParser\HHParser.exe" (
        echo ERROR: Failed to compile HHParser.
        pause
        exit /b 1
    ) else (
        set "EXE_PATH=%CD%\HHParser\HHParser.exe"
    )
) else (
    set "EXE_PATH=%CD%\HHParser.exe"
)

:: Удаляем временные папки
echo.
echo Cleaning up...
if exist "build" rmdir /s /q "build" 2>nul
if exist "*.spec" del *.spec 2>nul

:: Создаем папку для результатов
if not exist "hh_parse_results" mkdir "hh_parse_results"
if "%EXE_PATH%"=="" set "EXE_PATH=%CD%\HHParser.exe"¶

:: Создаем ярлык на рабочем столе
echo.
echo Creating desktop shortcut...
set "DESKTOP_PATH=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=HHParser.lnk"
set "ICON_PATH=%CD%\static\HHParse_logo.ico"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\%SHORTCUT_NAME%'); ^
$Shortcut.TargetPath = '%EXE_PATH%'; ^
$Shortcut.WorkingDirectory = '%CD%'; ^
if (Test-Path '%ICON_PATH%') { $Shortcut.IconLocation = '%ICON_PATH%'; } ^
$Shortcut.Save(); ^
Write-Host 'Desktop shortcut created successfully!'"

:: Создаем вспомогательный bat для запуска
echo @echo off > run_hhparser.bat
echo cd /d "%%~dp0" >> run_hhparser.bat
echo start "" "HHParser.exe" >> run_hhparser.bat
echo echo HHParser started! >> run_hhparser.bat

echo.
echo ====================================================
echo Installation completed!
echo Launch HHParser from desktop shortcut or run_hhparser.bat
echo ====================================================
echo.
if exist "HHParser.exe" (
    echo Executable: %EXE_PATH%
    echo Size:
    for %%I in ("HHParser.exe") do echo %%~zI bytes
) else (
    echo Executable folder: %CD%\HHParser\
    echo Size:
    for /f %%I in ('dir /s /b "HHParser\*.exe" 2^>nul ^| find /c /v ""') do echo Files: %%I
)
echo.
echo Playwright browsers location: C:\Program Files\ms-playwright
echo.
echo Created: run_parser.bat - for quick launch
echo.
pause