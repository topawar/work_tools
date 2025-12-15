from django.apps import AppConfig
from django.db.backends.signals import connection_created
import os
import sys
import logging

logger = logging.getLogger('work_tools')

class WorkToolsConfig(AppConfig):
    name = "work_tools"

    def ready(self):
        # 初始化临时目录
        self._init_temp_directories()
        
        def on_conn(sender, connection, **kwargs):
            try:
                if connection.vendor == "sqlite":
                    with connection.cursor() as c:
                        c.execute("PRAGMA journal_mode=WAL;")
                        c.execute("PRAGMA synchronous=NORMAL;")
                        c.execute("PRAGMA busy_timeout=30000;")
            except Exception:
                pass
        connection_created.connect(on_conn)
    
    def _init_temp_directories(self):
        """初始化必要的临时目录"""
        try:
            # 导入统一的运行时基础目录获取函数
            from .config import _get_runtime_base_dir
            base_dir = _get_runtime_base_dir()
            
            # 需要创建的目录列表
            temp_dirs = [
                os.path.join(base_dir, 'temp_files', 'sql_output'),
                os.path.join(base_dir, 'temp_files', 'downloads'),
                os.path.join(base_dir, 'temp_uploads', 'validation_failures'),
                os.path.join(base_dir, 'logs'),
                os.path.join(base_dir, 'config'),  # 确保sql配置目录存在
            ]
            
            for dir_path in temp_dirs:
                os.makedirs(dir_path, exist_ok=True)
            
            logger.info(f"[目录初始化] 临时目录初始化成功: {base_dir}")
        except Exception as e:
            logger.warning(f"[目录初始化] 临时目录创建失败: {e}")
