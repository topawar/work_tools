"""系统配置模块"""
from .views import (
    system_config_view,
    file_path_config_view,
    cleanup_config_view,
    select_folder_api,
    cleanup_now_view,
    download_sql
)
from .dropdown_config import (
    dropdown_config_view,
    dropdown_group_add,
    dropdown_group_edit,
    dropdown_group_toggle,
    dropdown_group_delete,
    dropdown_item_add,
    dropdown_item_edit,
    dropdown_item_delete,
    dropdown_item_toggle
)
from .configurable_config import (
    configurable_config_view,
    configurable_table_add,
    configurable_table_edit,
    configurable_table_toggle,
    configurable_table_delete,
    configurable_field_add,
    configurable_field_edit,
    configurable_field_delete,
    configurable_field_toggle
)
from .database_config import (
    database_config_view,
    database_config_add,
    database_config_edit,
    database_config_toggle,
    database_config_delete
)

__all__ = [
    # System config views
    'system_config_view',
    'file_path_config_view', 
    'cleanup_config_view',
    'select_folder_api',
    'cleanup_now_view',
    'download_sql',
    # Dropdown config
    'dropdown_config_view',
    'dropdown_group_add',
    'dropdown_group_edit',
    'dropdown_group_toggle',
    'dropdown_group_delete',
    'dropdown_item_add',
    'dropdown_item_edit',
    'dropdown_item_delete',
    'dropdown_item_toggle',
    # Configurable config
    'configurable_config_view',
    'configurable_table_add',
    'configurable_table_edit',
    'configurable_table_toggle',
    'configurable_table_delete',
    'configurable_field_add',
    'configurable_field_edit',
    'configurable_field_delete',
    'configurable_field_toggle',
    # Database config
    'database_config_view',
    'database_config_add',
    'database_config_edit',
    'database_config_toggle',
    'database_config_delete',
]
