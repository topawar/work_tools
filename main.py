#!/usr/bin/env python
"""
Work Tools 便携式应用程序主启动脚本
使用 waitress 作为生产服务器，whitenoise 处理静态文件
"""

import os
import sys
import webbrowser
import threading
import time
import socket
from pathlib import Path


def get_base_dir():
    """获取应用程序基础目录"""
    if getattr(sys, 'frozen', False):
        # 打包环境：可执行文件所在目录
        return Path(sys.executable).parent
    else:
        # 开发环境：脚本所在目录
        return Path(__file__).parent


def get_internal_dir():
    """获取内部资源目录"""
    base_dir = get_base_dir()
    if getattr(sys, 'frozen', False):
        return base_dir / '_internal'
    return base_dir


def setup_environment():
    """设置运行环境"""
    base_dir = get_base_dir()
    internal_dir = get_internal_dir()
    
    # 设置环境变量
    os.environ['DJANGO_SETTINGS_MODULE'] = 'work_tools.settings'
    
    # 数据库路径
    if getattr(sys, 'frozen', False):
        db_path = internal_dir / 'db.sqlite3'
        static_root = internal_dir / 'static'
    else:
        db_path = base_dir / 'db.sqlite3'
        static_root = base_dir / 'static'
    
    os.environ['WORK_TOOLS_DB_PATH'] = str(db_path)
    os.environ['WORK_TOOLS_STATIC_ROOT'] = str(static_root)
    os.environ['WORK_TOOLS_APP_DIR'] = str(base_dir)
    
    # 添加到Python路径
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    if str(internal_dir) not in sys.path:
        sys.path.insert(0, str(internal_dir))
    
    # 设置工作目录
    os.chdir(base_dir)
    
    return {
        'base_dir': base_dir,
        'internal_dir': internal_dir,
        'db_path': db_path,
        'static_root': static_root,
    }


def find_available_port(start_port=8000, end_port=8100):
    """查找可用端口"""
    for port in range(start_port, end_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None


def open_browser_delayed(url, delay=2):
    """延迟打开浏览器"""
    def _open():
        time.sleep(delay)
        webbrowser.open(url)
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def run_with_waitress(port):
    """使用waitress运行服务器"""
    try:
        from waitress import serve
        from django.core.wsgi import get_wsgi_application
        
        # 获取Django WSGI应用
        application = get_wsgi_application()
        
        print(f"使用 Waitress 服务器启动...")
        print(f"访问地址: http://127.0.0.1:{port}/")
        print("按 Ctrl+C 停止服务器...")
        print("=" * 60)
        
        # 启动waitress服务器
        serve(
            application,
            host='127.0.0.1',
            port=port,
            threads=4,
            url_scheme='http',
            _quiet=False,
        )
    except ImportError:
        print("Waitress 未安装，回退到 Django 开发服务器...")
        run_with_django_dev_server(port)


def run_with_django_dev_server(port):
    """使用Django开发服务器（备用）"""
    from django.core.management import execute_from_command_line
    
    cmd_args = ['manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload', '--insecure']
    
    print(f"使用 Django 开发服务器启动...")
    print(f"访问地址: http://127.0.0.1:{port}/")
    print("按 Ctrl+C 停止服务器...")
    print("=" * 60)
    
    sys.argv = cmd_args
    execute_from_command_line(sys.argv)


def main():
    """主函数"""
    print("=" * 60)
    print("Work Tools 便携式应用程序")
    print("=" * 60)
    
    try:
        # 设置环境
        env = setup_environment()
        
        print(f"运行模式: {'打包环境' if getattr(sys, 'frozen', False) else '开发环境'}")
        print(f"基础目录: {env['base_dir']}")
        print(f"数据库: {env['db_path']}")
        print(f"静态文件: {env['static_root']}")
        
        # 检查数据库
        if not env['db_path'].exists():
            print(f"错误: 数据库文件不存在: {env['db_path']}")
            input("按回车键退出...")
            return 1
        
        # 查找可用端口
        port = find_available_port()
        if not port:
            print("错误: 无法找到可用端口 (8000-8100)")
            input("按回车键退出...")
            return 1
        
        print(f"使用端口: {port}")
        
        # 初始化Django
        import django
        django.setup()
        
        # 延迟打开浏览器
        open_browser_delayed(f"http://127.0.0.1:{port}/")
        
        # 启动服务器（优先使用waitress）
        if getattr(sys, 'frozen', False):
            # 打包环境优先使用waitress
            run_with_waitress(port)
        else:
            # 开发环境使用Django开发服务器
            run_with_django_dev_server(port)
        
    except KeyboardInterrupt:
        print("\n应用程序已停止")
        return 0
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
