@echo off
chcp 65001 >nul
echo ====================================
echo Git 仓库清理与提交
echo ====================================
echo.

echo [1/3] 查看当前状态...
git status --short
echo.

echo ====================================
echo 准备提交以下更改：
echo.
echo ✅ 已完善 .gitignore（排除 600+ 个临时文件）
echo ✅ 已移除构建产物、临时文件、测试脚本
echo ✅ 保留所有核心业务代码
echo.
echo 新增功能：
echo   - 日志系统（中间件自动记录所有请求）
echo   - 系统配置管理
echo   - ERP终止页面
echo   - 浮动单价类型修改页面
echo ====================================
echo.

set /p confirm="确认提交吗？(y/n): "
if /i not "%confirm%"=="y" (
    echo 已取消提交
    pause
    exit /b
)

echo.
echo [2/3] 提交更改...
git commit -m "chore: 完善 .gitignore，排除构建产物和临时文件" -m "- 新增忽略规则：构建产物(build/, dist/)、临时文件、日志、测试脚本" -m "- 从 Git 跟踪移除 600+ 个不必要的文件" -m "- 保留核心业务代码和配置文件" -m "" -m "feat: 添加日志系统、系统配置和新页面功能" -m "" -m "新增功能：" -m "- 请求日志中间件：自动记录所有 HTTP 请求和响应" -m "- 系统配置管理：可视化配置界面" -m "- ERP终止页面：核电ERP终止功能" -m "- 浮动单价类型修改页面：支持单条和批量修改" -m "" -m "改进：" -m "- 统一导航菜单结构" -m "- 优化表单验证逻辑" -m "- 完善日志工具函数"

if %errorlevel% neq 0 (
    echo ❌ 提交失败！
    pause
    exit /b 1
)

echo ✅ 提交成功！
echo.

echo [3/3] 推送到远程...
set /p push="是否推送到远程仓库？(y/n): "
if /i "%push%"=="y" (
    git push origin main
    if %errorlevel% neq 0 (
        echo ❌ 推送失败！请检查网络连接或远程仓库配置
    ) else (
        echo ✅ 推送成功！
    )
) else (
    echo 已跳过推送，可稍后手动执行：git push origin main
)

echo.
echo ====================================
echo 完成！
echo ====================================
pause
