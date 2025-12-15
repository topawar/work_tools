from django.core.wsgi import get_wsgi_application
import os
import sys
import argparse
import webbrowser
import logging
from threading import Timer
import subprocess
import platform

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_tools.settings')

application = get_wsgi_application()

# 注意：不要在这里配置 logging，会覆盖 Django settings.py 中的配置
# 使用单独的 logger 来记录启动信息
runtime_logger = logging.getLogger('work_tools.runtime')

# 默认端口
DEFAULT_PORT = 8000


def kill_existing_process():
    """终止正在运行的Python进程（除了当前进程）"""
    try:
        current_pid = os.getpid()
        system = platform.system()
        
        if system == 'Windows':
            # Windows系统
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                encoding='gbk'  # Windows中文系统使用gbk编码
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # CSV格式: "python.exe","PID","...","..."
                        parts = line.replace('"', '').split(',')
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1].strip())
                                if pid != current_pid:
                                    # 终止其他Python进程
                                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                                 capture_output=True)
                                    runtime_logger.info(f'已终止进程 PID={pid}')
                            except (ValueError, IndexError):
                                continue
        else:
            # Linux/Mac系统
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'python' in line and 'run_app.py' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                if pid != current_pid:
                                    subprocess.run(['kill', '-9', str(pid)], 
                                                 capture_output=True)
                                    runtime_logger.info(f'已终止进程 PID={pid}')
                            except (ValueError, IndexError):
                                continue
    except Exception as e:
        runtime_logger.warning(f'终止旧进程失败: {e}')


def open_browser(port):
    try:
        webbrowser.open(f'http://127.0.0.1:{port}/')
    except Exception as e:
        runtime_logger.exception(e)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Work Tools - 合同数据维护工具')
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'指定服务端口号（默认: {DEFAULT_PORT}）'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='启动后不自动打开浏览器'
    )
    return parser.parse_args()


if __name__ == '__main__':
    try:
        # 解析命令行参数
        args = parse_args()
        port = args.port
        
        # 先终止正在运行的项目
        print('正在检查并终止旧进程...')
        kill_existing_process()
        print(f'开始启动项目... 端口: {port}')
        
        if not args.no_browser:
            Timer(1.0, lambda: open_browser(port)).start()
        
        try:
            from waitress import serve
            print(f'\n工作集已启动: http://127.0.0.1:{port}/')
            print('按 Ctrl+C 停止服务\n')
            serve(application, host='127.0.0.1', port=port)
        except Exception as e:
            runtime_logger.info('waitress 启动失败，回退到 wsgiref：%s', e)
            from wsgiref.simple_server import make_server
            httpd = make_server('127.0.0.1', port, application)
            print(f'\n工作集已启动: http://127.0.0.1:{port}/')
            print('按 Ctrl+C 停止服务\n')
            httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
    except Exception as e:
        runtime_logger.exception(e)
        print(f'启动失败: {e}')
        print('请查看日志文件: logs/')
        raise
