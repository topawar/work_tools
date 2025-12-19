"""
配置管理器模块
负责处理应用程序配置的加载、保存和持久化功能
"""

import os
import json
import sqlite3
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class AppConfig:
    """应用程序配置数据模型"""
    app_name: str = "Work Tools"
    version: str = "1.0.0"
    port: int = 8000
    debug: bool = False
    auto_open_browser: bool = True
    database_path: str = "db.sqlite3"
    static_root: str = "static"
    templates_root: str = "templates"
    logs_directory: str = "logs"
    temp_directory: str = "temp_files"
    secret_key: str = "django-insecure-default-key"
    allowed_hosts: list = None
    
    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = ['localhost', '127.0.0.1']
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建配置对象"""
        # 过滤掉不存在的字段
        valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class ConfigurationManager:
    """配置管理器类"""
    
    def __init__(self, config_path: str, db_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
            db_path: 数据库路径（用于持久化配置）
        """
        self.config_path = config_path
        self.db_path = db_path
        self.config = AppConfig()
        self.logger = logging.getLogger(__name__)
        
        # 确保配置目录存在（只在可写的情况下）
        try:
            config_dir = os.path.dirname(config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            # 在打包环境中，_internal目录可能是只读的，这是正常的
            self.logger.warning(f"无法创建配置目录（可能是只读环境）: {e}")
        
        # 初始化数据库表（如果使用数据库存储）
        if self.db_path:
            self._init_config_table()
    
    def _init_config_table(self):
        """初始化配置表"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"初始化配置表失败: {e}")
    
    def load_config(self) -> AppConfig:
        """
        加载配置文件
        优先级：数据库配置 > JSON文件配置 > 默认配置
        """
        try:
            # 首先尝试从数据库加载
            if self.db_path and os.path.exists(self.db_path):
                db_config = self._load_from_database()
                if db_config:
                    self.config = AppConfig.from_dict(db_config)
                    self.logger.info("从数据库加载配置成功")
                    return self.config
            
            # 然后尝试从JSON文件加载
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.config = AppConfig.from_dict(config_data)
                    self.logger.info("从JSON文件加载配置成功")
                    return self.config
            
            # 使用默认配置
            self.logger.info("使用默认配置")
            return self.config
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return self.config
    
    def _load_from_database(self) -> Optional[Dict[str, Any]]:
        """从数据库加载配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT key, value FROM app_config")
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None
            
            config_data = {}
            for key, value in rows:
                try:
                    # 尝试解析JSON值
                    parsed_value = json.loads(value)
                    config_data[key] = parsed_value
                except json.JSONDecodeError:
                    # 如果不是JSON，直接使用字符串值
                    config_data[key] = value
            
            return config_data
            
        except Exception as e:
            self.logger.error(f"从数据库加载配置失败: {e}")
            return None
    
    def save_config(self, config: Optional[AppConfig] = None) -> bool:
        """
        保存配置文件
        同时保存到JSON文件和数据库
        """
        if config:
            self.config = config
        
        try:
            # 保存到JSON文件
            config_data = self.config.to_dict()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # 保存到数据库
            if self.db_path:
                self._save_to_database(config_data)
            
            self.logger.info("配置保存成功")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False
    
    def _save_to_database(self, config_data: Dict[str, Any]):
        """保存配置到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 清除旧配置
            conn.execute("DELETE FROM app_config")
            
            # 插入新配置
            for key, value in config_data.items():
                # 始终将值序列化为JSON字符串以保持一致性
                json_value = json.dumps(value, ensure_ascii=False)
                conn.execute(
                    "INSERT INTO app_config (key, value) VALUES (?, ?)",
                    (key, json_value)
                )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存配置到数据库失败: {e}")
    
    def update_config(self, **kwargs) -> bool:
        """
        更新配置项
        
        Args:
            **kwargs: 要更新的配置项
        """
        try:
            config_dict = self.config.to_dict()
            config_dict.update(kwargs)
            
            # 验证配置项
            new_config = AppConfig.from_dict(config_dict)
            
            # 验证新配置
            temp_config = self.config
            self.config = new_config
            
            if not self.validate_config():
                self.config = temp_config
                self.logger.error("配置验证失败")
                return False
            
            # 保存更新后的配置
            return self.save_config(new_config)
            
        except Exception as e:
            self.logger.error(f"更新配置失败: {e}")
            return False
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self.config, key, default)
    
    def update_django_settings(self):
        """更新Django设置"""
        try:
            from django.conf import settings
            
            # 更新数据库配置
            if hasattr(settings, 'DATABASES'):
                db_path = os.path.join(
                    os.path.dirname(self.config_path),
                    self.config.database_path
                )
                settings.DATABASES['default']['NAME'] = db_path
            
            # 更新静态文件配置
            if hasattr(settings, 'STATIC_ROOT'):
                static_path = os.path.join(
                    os.path.dirname(self.config_path),
                    self.config.static_root
                )
                settings.STATIC_ROOT = static_path
            
            # 更新模板配置
            if hasattr(settings, 'TEMPLATES'):
                templates_path = os.path.join(
                    os.path.dirname(self.config_path),
                    self.config.templates_root
                )
                for template_config in settings.TEMPLATES:
                    if 'DIRS' in template_config:
                        template_config['DIRS'] = [templates_path]
            
            # 更新调试模式
            settings.DEBUG = self.config.debug
            
            # 更新允许的主机
            settings.ALLOWED_HOSTS = self.config.allowed_hosts
            
            # 更新密钥
            settings.SECRET_KEY = self.config.secret_key
            
            self.logger.info("Django设置更新成功")
            return True
            
        except Exception as e:
            self.logger.error(f"更新Django设置失败: {e}")
            return False
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证端口范围
            if not (1024 <= self.config.port <= 65535):
                self.logger.error(f"端口号无效: {self.config.port}")
                return False
            
            # 验证必要的目录路径
            required_paths = [
                self.config.static_root,
                self.config.templates_root,
                self.config.logs_directory,
                self.config.temp_directory
            ]
            
            for path in required_paths:
                if not path or '..' in path:
                    self.logger.error(f"路径无效: {path}")
                    return False
            
            # 验证应用名称
            if not self.config.app_name or len(self.config.app_name.strip()) == 0:
                self.logger.error("应用名称不能为空")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        try:
            self.config = AppConfig()
            return self.save_config()
        except Exception as e:
            self.logger.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到指定路径"""
        try:
            config_data = self.config.to_dict()
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置导出成功: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """从指定路径导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            new_config = AppConfig.from_dict(config_data)
            
            # 验证导入的配置
            temp_config = self.config
            self.config = new_config
            
            if not self.validate_config():
                self.config = temp_config
                self.logger.error("导入的配置无效")
                return False
            
            # 保存导入的配置
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return False