@echo off
setlocal enabledelayedexpansion

:: ====================================================================
:: Work Tools Package Tool
:: ====================================================================

echo.
echo ========================================
echo Work Tools Package Tool
echo ========================================
echo.

:: Check PyInstaller
echo [1/7] Checking environment...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller not installed
    echo Please run: pip install pyinstaller
    pause
    exit /b 1
)
echo [OK] PyInstaller installed

:: Check database file
echo.
echo [2/7] Checking database file...
if not exist "db.sqlite3" (
    echo [WARNING] Database file not found, creating...
    python manage.py migrate
    if errorlevel 1 (
        echo [ERROR] Database migration failed
        pause
        exit /b 1
    )
    echo [OK] Database file created
) else (
    echo [OK] Database file exists
)

:: Select package mode
echo.
echo [3/7] Select package mode
echo.
echo Choose package type:
echo   1. Directory mode (Recommended) - Generate exe and dependency folder
echo   2. Single file mode - Generate single exe file
echo   3. Both modes
echo.
set /p choice="Enter option (1/2/3): "

if "%choice%"=="1" (
    set "mode=onedir"
    set "mode_name=Directory mode"
) else if "%choice%"=="2" (
    set "mode=onefile"
    set "mode_name=Single file mode"
) else if "%choice%"=="3" (
    set "mode=both"
    set "mode_name=Both modes"
) else (
    echo [ERROR] Invalid option
    pause
    exit /b 1
)

echo.
echo [OK] Selected: %mode_name%

:: Clean old build
echo.
echo [4/7] Cleaning old build...
if exist "dist" (
    echo Deleting dist directory...
    rmdir /s /q "dist" 2>nul
)
if exist "build" (
    echo Deleting build directory...
    rmdir /s /q "build" 2>nul
)
echo [OK] Clean completed

:: Execute packaging
echo.
echo [5/7] Start packaging...
echo.

if "%mode%"=="onedir" (
    echo Executing directory mode packaging...
    pyinstaller work_tools_onedir.spec --noconfirm
    if errorlevel 1 (
        echo [ERROR] Directory mode packaging failed
        pause
        exit /b 1
    )
    echo [OK] Directory mode packaging completed
) else if "%mode%"=="onefile" (
    echo Executing single file mode packaging...
    pyinstaller work_tools_onefile.spec --noconfirm
    if errorlevel 1 (
        echo [ERROR] Single file mode packaging failed
        pause
        exit /b 1
    )
    echo [OK] Single file mode packaging completed
) else if "%mode%"=="both" (
    echo Executing directory mode packaging...
    pyinstaller work_tools_onedir.spec --noconfirm
    if errorlevel 1 (
        echo [ERROR] Directory mode packaging failed
        pause
        exit /b 1
    )
    echo [OK] Directory mode packaging completed
    
    echo.
    echo Executing single file mode packaging...
    pyinstaller work_tools_onefile.spec --noconfirm
    if errorlevel 1 (
        echo [ERROR] Single file mode packaging failed
        pause
        exit /b 1
    )
    echo [OK] Single file mode packaging completed
)

:: Verify result
echo.
echo [6/7] Verifying packaging result...

if "%mode%"=="onedir" (
    if exist "dist\work_tools_package\work_tools_package.exe" (
        echo [OK] Directory mode: dist\work_tools_package\work_tools_package.exe
    ) else (
        echo [ERROR] Directory mode package not found
        pause
        exit /b 1
    )
) else if "%mode%"=="onefile" (
    if exist "dist\work_tools_package.exe" (
        echo [OK] Single file mode: dist\work_tools_package.exe
    ) else (
        echo [ERROR] Single file mode package not found
        pause
        exit /b 1
    )
) else if "%mode%"=="both" (
    set "success=1"
    if exist "dist\work_tools_package\work_tools_package.exe" (
        echo [OK] Directory mode: dist\work_tools_package\work_tools_package.exe
    ) else (
        echo [ERROR] Directory mode package not found
        set "success=0"
    )
    if exist "dist\work_tools_package.exe" (
        echo [OK] Single file mode: dist\work_tools_package.exe
    ) else (
        echo [ERROR] Single file mode package not found
        set "success=0"
    )
    if "!success!"=="0" (
        pause
        exit /b 1
    )
)

:: Packaging completed
echo.
echo [7/7] Packaging completed!
echo.
echo ========================================
echo Package Information
echo ========================================
echo Package mode: %mode_name%
echo Output directory: dist\
echo.

if "%mode%"=="onedir" (
    echo How to run:
    echo   dist\work_tools_package\work_tools_package.exe
    echo   dist\work_tools_package\work_tools_package.exe --port 8080
    echo   dist\work_tools_package\work_tools_package.exe --no-browser
) else if "%mode%"=="onefile" (
    echo How to run:
    echo   dist\work_tools_package.exe
    echo   dist\work_tools_package.exe --port 8080
    echo   dist\work_tools_package.exe --no-browser
) else if "%mode%"=="both" (
    echo How to run:
    echo   Directory mode: dist\work_tools_package\work_tools_package.exe
    echo   Single file mode: dist\work_tools_package.exe
    echo.
    echo Parameters:
    echo   --port 8080      : Specify port
    echo   --no-browser     : Do not open browser automatically
)

echo.
echo ========================================
echo.
echo Tips: 
echo   1. First run will create temp directories automatically
echo   2. Log files: logs\
echo   3. SQL output: temp_files\sql_output\
echo   4. SQL output path can be configured via UI
echo.

pause
