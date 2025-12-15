@echo off
chcp 65001 >nul
echo ========================================
echo Work Tools 打包版本快速测试
echo ========================================
echo.

set "PACKAGE_DIR=dist\work_tools_package"

if not exist "%PACKAGE_DIR%\work_tools.exe" (
    echo [错误] 未找到打包文件
    echo 请先运行打包命令：python -m PyInstaller work_tools_onedir.spec --clean --noconfirm
    pause
    exit /b 1
)

echo [1/5] 检查打包目录结构...
if exist "%PACKAGE_DIR%\_internal\tcl86t.dll" (
    echo ✓ tkinter依赖已打包
) else (
    echo ✗ tkinter依赖缺失
)

if exist "%PACKAGE_DIR%\_internal\_tkinter.pyd" (
    echo ✓ tkinter模块已打包
) else (
    echo ✗ tkinter模块缺失
)

echo.
echo [2/5] 创建测试目录...
set "TEST_DIR=test_package_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TEST_DIR=%TEST_DIR: =0%"

if exist "%TEST_DIR%" rmdir /s /q "%TEST_DIR%"
mkdir "%TEST_DIR%"

echo.
echo [3/5] 复制打包文件到测试目录...
xcopy "%PACKAGE_DIR%" "%TEST_DIR%\work_tools_package\" /E /I /Q >nul
echo ✓ 复制完成

echo.
echo [4/5] 测试打包版本...
echo 即将启动打包版本，请执行以下测试：
echo.
echo 1. 检查浏览器是否自动打开
echo 2. 访问 系统配置 -^> 文件路径配置
echo 3. 点击"选择文件夹"按钮，验证tkinter对话框是否弹出
echo 4. 配置一个自定义路径并保存
echo 5. 执行任意功能生成SQL文件
echo 6. 检查SQL文件是否生成到正确路径
echo.
echo 按任意键启动测试...
pause >nul

cd /d "%TEST_DIR%\work_tools_package"
start "" work_tools.exe --port 8090

echo.
echo [5/5] 测试提示
echo ========================================
echo 应用已启动，端口：8090
echo 测试目录：%CD%
echo.
echo 测试完成后请检查：
echo - 是否自动创建了 config、logs、temp_files 等目录
echo - 配置文件是否保存在 config\app_config.json
echo - SQL文件是否生成到配置的路径
echo.
echo 查看日志：logs\work_tools.log
echo ========================================
echo.
pause
