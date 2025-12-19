"""系统配置模块"""
from .views import (
    system_config_view,
    file_path_config_view,
    cleanup_config_view,
    select_folder_api,
    cleanup_now_view
)

__all__ = [
    'system_config_view',
    'file_path_config_view', 
    'cleanup_config_view',
    'select_folder_api',
    'cleanup_now_view'
]
