"""
应用启动器模块
负责管理应用程序的启动流程、端口检测、Django服务器启动和浏览器集成
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess
import logging
import signal
# import psutil  # 可选依赖，如果需要进程管理功能
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LaunchStatus:
    """启动状态数据模型"""
    is_running: bool = False
    server_port: int = None
    server_url: str = None
    pid: int = None
    start_time: datetime = None
    error_message: str = None
    
    def update_status(self, **kwargs):
        """更新状态信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class ApplicationLauncher:
    """应用启动器类"""
    
    def __init__(self, app_dir: str, config_manager=None):
        """
        初始化应用启动器
        
        Args:
            app_dir: 应用程序目录
            config_manager: 配置管理器实例
        """
        self.app_dir = os.path.abspath(app_dir)
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 启动状态
        self.status = LaunchStatus()
        
        # 默认配置
        self.default_port = 8000
        self.port_range = (8000, 8100)
        self.startup_timeout = 30  # 秒
        
        # Django服务器进程
        self.server_process = None
        self.server_thread = None
        
        # 设置日志
        self._setup_logging()
        
        # 检测现有实例
        self.existing_instance_port = self._detect_existing_instance()
    
    def _setup_logging(self):
        """设置日志配置"""
        log_dir = os.path.join(self.app_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "launcher.log")
        
        # 配置文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 配置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def start(self) -> bool:
        """
        启动应用程序主流程
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.logger.info("开始启动Work Tools应用程序...")
            
            # 检查是否已有实例运行
            if self.existing_instance_port:
                self.logger.info(f"检测到现有实例运行在端口 {self.existing_instance_port}")
                self._open_browser(f"http://127.0.0.1:{self.existing_instance_port}")
                return True
            
            # 设置运行环境
            if not self._setup_environment():
                return False
            
            # 查找可用端口
            port = self._find_available_port()
            if not port:
                self.logger.error("无法找到可用端口")
                return False
            
            # 启动Django服务器
            if not self._start_django_server(port):
                return False
            
            # 等待服务器启动
            if not self._wait_for_server_ready(port):
                return False
            
            # 更新状态
            self.status.update_status(
                is_running=True,
                server_port=port,
                server_url=f"http://127.0.0.1:{port}",
                pid=os.getpid(),
                start_time=datetime.now()
            )
            
            # 打开浏览器
            if self._should_open_browser():
                self._open_browser(self.status.server_url)
            
            self.logger.info(f"应用程序启动成功，访问地址: {self.status.server_url}")
            return True
            
        except Exception as e:
            error_msg = f"启动失败: {e}"
            self.logger.error(error_msg)
            self.status.update_status(error_message=error_msg)
            return False
    
    def _setup_environment(self) -> bool:
        """设置运行环境"""
        try:
            # 设置Django设置模块
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_tools.settings')
            
            # 添加应用目录到Python路径
            if self.app_dir not in sys.path:
                sys.path.insert(0, self.app_dir)
            
            # 设置工作目录
            os.chdir(self.app_dir)
            
            # 初始化Django
            try:
                import django
                django.setup()
                self.logger.info("Django环境初始化成功")
            except Exception as e:
                self.logger.error(f"Django初始化失败: {e}")
                return False
            
            # 更新配置管理器设置
            if self.config_manager:
                self.config_manager.update_django_settings()
            
            return True
            
        except Exception as e:
            self.logger.error(f"环境设置失败: {e}")
            return False
    
    def _find_available_port(self) -> Optional[int]:
        """查找可用端口"""
        # 首先尝试配置中的端口
        if self.config_manager:
            preferred_port = self.config_manager.get_config_value('port', self.default_port)
            if self._is_port_available(preferred_port):
                return preferred_port
        
        # 在端口范围内查找可用端口
        for port in range(self.port_range[0], self.port_range[1] + 1):
            if self._is_port_available(port):
                return port
        
        return None
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0
        except Exception:
            return False
    
    def _detect_existing_instance(self) -> Optional[int]:
        """检测现有运行实例"""
        try:
            # 检查常用端口范围
            for port in range(self.port_range[0], self.port_range[1] + 1):
                if not self._is_port_available(port):
                    # 尝试访问该端口，看是否是我们的应用
                    if self._is_our_application(port):
                        return port
            return None
        except Exception as e:
            self.logger.warning(f"检测现有实例时出错: {e}")
            return None
    
    def _is_our_application(self, port: int) -> bool:
        """检查指定端口是否运行着我们的应用"""
        try:
            import urllib.request
            import urllib.error
            
            url = f"http://127.0.0.1:{port}/"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'WorkTools-Launcher')
            
            with urllib.request.urlopen(request, timeout=2) as response:
                content = response.read().decode('utf-8')
                # 检查响应中是否包含我们应用的特征
                return 'Work Tools' in content or 'Django' in content
                
        except Exception:
            return False
    
    def _start_django_server(self, port: int) -> bool:
        """启动Django开发服务器"""
        try:
            # 在单独线程中启动服务器
            self.server_thread = threading.Thread(
                target=self._run_django_server,
                args=(port,),
                daemon=True
            )
            self.server_thread.start()
            
            self.logger.info(f"Django服务器启动线程已创建，端口: {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动Django服务器失败: {e}")
            return False
    
    def _run_django_server(self, port: int):
        """在线程中运行Django服务器"""
        try:
            from django.core.management import execute_from_command_line
            
            # 构建Django runserver命令
            cmd_args = [
                'manage.py',
                'runserver',
                f'127.0.0.1:{port}',
                '--noreload',  # 禁用自动重载
            ]
            
            # 在打包环境中添加--insecure参数，允许在DEBUG=False时提供静态文件
            if getattr(sys, 'frozen', False):
                cmd_args.append('--insecure')
            
            sys.argv = cmd_args
            
            self.logger.info(f"启动Django服务器: 127.0.0.1:{port}")
            execute_from_command_line(sys.argv)
            
        except Exception as e:
            self.logger.error(f"Django服务器运行出错: {e}")
    
    def _wait_for_server_ready(self, port: int, timeout: int = None) -> bool:
        """等待服务器就绪"""
        timeout = timeout or self.startup_timeout
        start_time = time.time()
        
        self.logger.info(f"等待服务器就绪，超时时间: {timeout}秒")
        
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', port))
                    if result == 0:
                        # 端口已开放，再等待一下确保服务完全就绪
                        time.sleep(1)
                        self.logger.info("服务器就绪")
                        return True
            except Exception:
                pass
            
            time.sleep(0.5)
        
        self.logger.error(f"服务器启动超时 ({timeout}秒)")
        return False
    
    def _should_open_browser(self) -> bool:
        """判断是否应该打开浏览器"""
        if self.config_manager:
            return self.config_manager.get_config_value('auto_open_browser', True)
        return True
    
    def _open_browser(self, url: str):
        """打开默认浏览器"""
        try:
            self.logger.info(f"打开浏览器: {url}")
            webbrowser.open(url)
        except Exception as e:
            self.logger.warning(f"打开浏览器失败: {e}")
    
    def stop(self) -> bool:
        """停止应用程序"""
        try:
            self.logger.info("正在停止应用程序...")
            
            # 停止Django服务器线程
            if self.server_thread and self.server_thread.is_alive():
                # 由于Django服务器在线程中运行，我们需要通过其他方式停止
                # 这里可以设置一个停止标志或使用其他机制
                pass
            
            # 更新状态
            self.status.update_status(
                is_running=False,
                server_port=None,
                server_url=None
            )
            
            self.logger.info("应用程序已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止应用程序失败: {e}")
            return False
    
    def restart(self) -> bool:
        """重启应用程序"""
        try:
            self.logger.info("正在重启应用程序...")
            
            if not self.stop():
                return False
            
            # 等待一下确保完全停止
            time.sleep(2)
            
            return self.start()
            
        except Exception as e:
            self.logger.error(f"重启应用程序失败: {e}")
            return False
    
    def get_status(self) -> LaunchStatus:
        """获取运行状态"""
        return self.status
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        info = {
            'status': 'running' if self.status.is_running else 'stopped',
            'port': self.status.server_port,
            'url': self.status.server_url,
            'pid': self.status.pid,
            'start_time': self.status.start_time.isoformat() if self.status.start_time else None,
            'uptime': None,
            'error_message': self.status.error_message
        }
        
        if self.status.start_time:
            uptime = datetime.now() - self.status.start_time
            info['uptime'] = str(uptime)
        
        return info
    
    def check_health(self) -> Tuple[bool, str]:
        """检查应用程序健康状态"""
        try:
            if not self.status.is_running:
                return False, "应用程序未运行"
            
            if not self.status.server_port:
                return False, "服务器端口未设置"
            
            # 检查端口是否仍然被占用
            if self._is_port_available(self.status.server_port):
                return False, f"端口 {self.status.server_port} 不再被占用"
            
            # 尝试访问服务器
            try:
                import urllib.request
                url = f"http://127.0.0.1:{self.status.server_port}/"
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.getcode() == 200:
                        return True, "应用程序运行正常"
                    else:
                        return False, f"服务器响应异常: {response.getcode()}"
            except Exception as e:
                return False, f"无法访问服务器: {e}"
                
        except Exception as e:
            return False, f"健康检查失败: {e}"
    
    def display_startup_info(self):
        """显示启动信息"""
        print("=" * 60)
        print("Work Tools 便携式应用程序")
        print("=" * 60)
        
        if self.existing_instance_port:
            print(f"✓ 检测到现有实例运行在端口 {self.existing_instance_port}")
            print(f"✓ 浏览器将打开到: http://127.0.0.1:{self.existing_instance_port}")
        elif self.status.is_running:
            print(f"✓ 服务器启动成功")
            print(f"✓ 访问地址: {self.status.server_url}")
            print(f"✓ 进程ID: {self.status.pid}")
            print(f"✓ 启动时间: {self.status.start_time}")
        else:
            print("✗ 启动失败")
            if self.status.error_message:
                print(f"✗ 错误信息: {self.status.error_message}")
        
        print("=" * 60)
        print("按 Ctrl+C 停止应用程序")
        print("=" * 60)
    
    def run_interactive(self):
        """交互式运行模式"""
        try:
            # 启动应用程序
            if self.start():
                self.display_startup_info()
                
                # 等待用户中断
                try:
                    while self.status.is_running:
                        time.sleep(1)
                        
                        # 定期检查健康状态
                        if time.time() % 30 == 0:  # 每30秒检查一次
                            is_healthy, message = self.check_health()
                            if not is_healthy:
                                self.logger.warning(f"健康检查失败: {message}")
                                
                except KeyboardInterrupt:
                    print("\n正在停止应用程序...")
                    self.stop()
            else:
                self.display_startup_info()
                return False
                
        except Exception as e:
            self.logger.error(f"交互式运行失败: {e}")
            return False
        
        return True