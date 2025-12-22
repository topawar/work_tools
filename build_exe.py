"""
Work Tools 便携式可执行文件打包脚本
使用 PyInstaller 打包 Django 应用为独立可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "work_tools.spec"

# 输出目录
OUTPUT_DIR = DIST_DIR / "WorkTools"

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(message):
    """打印步骤信息"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")

def print_success(message):
    """打印成功信息"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    """打印错误信息"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_warning(message):
    """打印警告信息"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def check_dependencies():
    """检查必要的依赖"""
    print_step("检查依赖")
    
    missing = []
    
    # 检查 PyInstaller
    try:
        import PyInstaller
        print_success(f"PyInstaller 已安装 (版本: {PyInstaller.__version__})")
    except ImportError:
        missing.append("pyinstaller")
        print_error("PyInstaller 未安装")
    
    # 检查 Django
    try:
        import django
        print_success(f"Django 已安装 (版本: {django.__version__})")
    except ImportError:
        missing.append("django")
        print_error("Django 未安装")
    
    # 检查其他依赖
    deps = {
        'waitress': 'Waitress',
        'openpyxl': 'OpenPyXL',
        'pypinyin': 'PyPinyin',
        'psutil': 'psutil'
    }
    
    for module, name in deps.items():
        try:
            __import__(module)
            print_success(f"{name} 已安装")
        except ImportError:
            missing.append(module)
            print_error(f"{name} 未安装")
    
    if missing:
        print_error(f"\n缺少依赖: {', '.join(missing)}")
        print(f"\n请运行: pip install {' '.join(missing)}")
        return False
    
    return True

def collect_static_files():
    """收集 Django 静态文件"""
    print_step("收集静态文件")
    
    try:
        # 运行 collectstatic
        result = subprocess.run(
            [sys.executable, "manage.py", "collectstatic", "--noinput", "--clear"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("静态文件收集成功")
            return True
        else:
            print_error(f"静态文件收集失败: {result.stderr}")
            return False
    except Exception as e:
        print_error(f"静态文件收集出错: {e}")
        return False

def clean_build_dirs():
    """清理构建目录"""
    print_step("清理旧的构建文件")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print_success(f"已删除: {dir_path}")
            except Exception as e:
                print_warning(f"无法删除 {dir_path}: {e}")
        else:
            print(f"目录不存在: {dir_path}")

def copy_database():
    """复制数据库文件到输出目录"""
    print_step("复制数据库文件")
    
    db_file = PROJECT_ROOT / "db.sqlite3"
    
    if not db_file.exists():
        print_warning("数据库文件不存在，将创建空数据库")
        return True
    
    try:
        # 确保输出目录存在
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 复制数据库
        dest_db = OUTPUT_DIR / "db.sqlite3"
        shutil.copy2(db_file, dest_db)
        print_success(f"数据库已复制到: {dest_db}")
        return True
    except Exception as e:
        print_error(f"复制数据库失败: {e}")
        return False

def run_pyinstaller():
    """运行 PyInstaller"""
    print_step("运行 PyInstaller 打包")
    
    if not SPEC_FILE.exists():
        print_error(f"Spec 文件不存在: {SPEC_FILE}")
        return False
    
    try:
        # 运行 PyInstaller
        cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(SPEC_FILE)
        ]
        
        print(f"执行命令: {' '.join(cmd)}\n")
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True
        )
        
        if result.returncode == 0:
            print_success("PyInstaller 打包成功")
            return True
        else:
            print_error("PyInstaller 打包失败")
            return False
    except Exception as e:
        print_error(f"PyInstaller 执行出错: {e}")
        return False

def create_readme():
    """创建 README 文件"""
    print_step("创建 README 文件")
    
    readme_content = f"""# Work Tools 便携版

## 版本信息
- 打包日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Python 版本: {sys.version.split()[0]}

## 使用说明

### 启动应用
双击 `WorkTools.exe` 启动应用程序。

应用会自动：
1. 启动内置的 Web 服务器
2. 打开默认浏览器访问应用

### 访问地址
- 默认地址: http://127.0.0.1:8000

### 停止应用
关闭命令行窗口即可停止应用。

### 数据文件
- 数据库文件: `db.sqlite3`
- 配置文件: `config/app_config.json`
- 日志文件: `logs/` 目录

### 注意事项
1. 首次运行可能需要几秒钟启动时间
2. 请勿删除或移动 `_internal` 目录
3. 数据库文件包含所有配置和数据，请定期备份

### 故障排除
如果遇到问题：
1. 检查 `logs/` 目录下的日志文件
2. 确保端口 8000 未被占用
3. 以管理员权限运行

## 技术支持
如有问题，请查看日志文件或联系技术支持。
"""
    
    try:
        readme_file = OUTPUT_DIR / "README.txt"
        readme_file.write_text(readme_content, encoding='utf-8')
        print_success(f"README 已创建: {readme_file}")
        return True
    except Exception as e:
        print_error(f"创建 README 失败: {e}")
        return False

def create_config_dirs():
    """创建必要的配置目录"""
    print_step("创建配置目录")
    
    dirs = [
        OUTPUT_DIR / "logs",
        OUTPUT_DIR / "config",
        OUTPUT_DIR / "media",
    ]
    
    for dir_path in dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print_success(f"目录已创建: {dir_path}")
        except Exception as e:
            print_error(f"创建目录失败 {dir_path}: {e}")
            return False
    
    # 复制配置文件
    config_src = PROJECT_ROOT / "config" / "app_config.json"
    if config_src.exists():
        try:
            config_dest = OUTPUT_DIR / "config" / "app_config.json"
            shutil.copy2(config_src, config_dest)
            print_success(f"配置文件已复制: {config_dest}")
        except Exception as e:
            print_warning(f"复制配置文件失败: {e}")
    
    return True

def verify_build():
    """验证构建结果"""
    print_step("验证构建结果")
    
    exe_file = OUTPUT_DIR / "WorkTools.exe"
    
    if not exe_file.exists():
        print_error(f"可执行文件不存在: {exe_file}")
        return False
    
    print_success(f"可执行文件已生成: {exe_file}")
    
    # 检查文件大小
    size_mb = exe_file.stat().st_size / (1024 * 1024)
    print(f"文件大小: {size_mb:.2f} MB")
    
    # 检查必要的目录
    required_dirs = ["_internal", "logs", "config"]
    for dir_name in required_dirs:
        dir_path = OUTPUT_DIR / dir_name
        if dir_path.exists():
            print_success(f"目录存在: {dir_name}")
        else:
            print_warning(f"目录缺失: {dir_name}")
    
    # 检查数据库
    db_file = OUTPUT_DIR / "db.sqlite3"
    if db_file.exists():
        db_size_mb = db_file.stat().st_size / (1024 * 1024)
        print_success(f"数据库文件存在 ({db_size_mb:.2f} MB)")
    else:
        print_warning("数据库文件不存在")
    
    return True

def main():
    """主函数"""
    print(f"\n{Colors.HEADER}{'='*60}")
    print("Work Tools 便携版打包工具")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    # 1. 检查依赖
    if not check_dependencies():
        print_error("\n依赖检查失败，请安装缺失的依赖后重试")
        return 1
    
    # 2. 收集静态文件
    if not collect_static_files():
        print_error("\n静态文件收集失败")
        return 1
    
    # 3. 清理旧的构建文件
    clean_build_dirs()
    
    # 4. 运行 PyInstaller
    if not run_pyinstaller():
        print_error("\nPyInstaller 打包失败")
        return 1
    
    # 5. 复制数据库
    if not copy_database():
        print_warning("\n数据库复制失败，但继续构建")
    
    # 6. 创建配置目录
    if not create_config_dirs():
        print_error("\n配置目录创建失败")
        return 1
    
    # 7. 创建 README
    create_readme()
    
    # 8. 验证构建
    if not verify_build():
        print_error("\n构建验证失败")
        return 1
    
    # 完成
    print(f"\n{Colors.OKGREEN}{'='*60}")
    print("✓ 打包完成！")
    print(f"{'='*60}{Colors.ENDC}\n")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"可执行文件: {OUTPUT_DIR / 'WorkTools.exe'}")
    print(f"\n运行 {OUTPUT_DIR / 'WorkTools.exe'} 启动应用\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_error("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
