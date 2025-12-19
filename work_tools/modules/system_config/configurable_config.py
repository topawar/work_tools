"""可配置表管理视图"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.cache import cache

from work_tools.models import ConfigurableTable, ConfigurableField, DropdownGroup
from work_tools.navigation import get_sidebar_groups

logger = logging.getLogger('work_tools.view')


def configurable_config_view(request):
    """配置管理主页面"""
    try:
        from work_tools.models import DatabaseConfig
        from work_tools.utils.pagination_helper import filter_by_search, paginate_queryset
        
        # 获取所有表配置
        tables = ConfigurableTable.objects.all().order_by('sort_order', 'table_code')
        
        # 获取所有数据库配置
        all_db_configs = DatabaseConfig.objects.filter(is_active=True).order_by('sort_order', 'config_code')
        
        # 获取当前选中的表
        selected_table_id = request.GET.get('table_id')
        if selected_table_id:
            selected_table = get_object_or_404(ConfigurableTable, id=selected_table_id)
        elif tables.exists():
            selected_table = tables.first()
        else:
            selected_table = None
        
        # 获取搜索关键词和分页参数
        field_search = request.GET.get('field_search', '').strip()
        update_page = request.GET.get('update_page')
        if not update_page or update_page == '':
            update_page = 1
        query_page = request.GET.get('query_page')
        if not query_page or query_page == '':
            query_page = 1
        
        # 获取当前表的字段配置（分类显示、支持搜索和分页）
        update_fields_page = None
        query_fields_page = None
        if selected_table:
            # 修改字段
            update_fields_query = ConfigurableField.objects.filter(
                table=selected_table,
                field_type='update'
            )
            if field_search:
                update_fields_query = filter_by_search(
                    update_fields_query, 
                    field_search, 
                    ['field_name', 'display_name']
                )
            update_fields_query = update_fields_query.order_by('sort_order', 'field_name')
            update_fields_page = paginate_queryset(update_fields_query, update_page, per_page=10)
            
            # 查询字段
            query_fields_query = ConfigurableField.objects.filter(
                table=selected_table,
                field_type='query'
            )
            if field_search:
                query_fields_query = filter_by_search(
                    query_fields_query, 
                    field_search, 
                    ['field_name', 'display_name']
                )
            query_fields_query = query_fields_query.order_by('sort_order', 'field_name')
            query_fields_page = paginate_queryset(query_fields_query, query_page, per_page=10)
        
        # 获取所有下拉框分组
        dropdown_groups = DropdownGroup.objects.filter(is_active=True).order_by('group_code')
        
        # 获取操作消息
        message = request.GET.get('message', '')
        error = request.GET.get('error', '')
        
        return render(request, 'modules/system_config/configurable_config.html', {
            'tables': tables,
            'selected_table': selected_table,
            'update_fields_page': update_fields_page,
            'query_fields_page': query_fields_page,
            'field_search': field_search,
            'all_db_configs': all_db_configs,
            'dropdown_groups': dropdown_groups,
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'configurable_config',
            'message': message,
            'error': error,
        })
    except Exception as e:
        logger.error(f"[配置管理] 加载页面失败: {e}")
        return render(request, 'modules/system_config/configurable_config.html', {
            'tables': [],
            'selected_table': None,
            'update_fields_page': None,
            'query_fields_page': None,
            'field_search': '',
            'all_db_configs': [],
            'dropdown_groups': [],
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'configurable_config',
            'error': f'加载失败: {str(e)}',
        })


@require_POST
def configurable_table_add(request):
    """添加表配置"""
    try:
        table_name = request.POST.get('table_name', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        description = request.POST.get('description', '').strip()
        db_config_ids = request.POST.getlist('db_configs')  # 获取选中的数据库配置
        
        # 验证输入
        if not table_name or not display_name:
            return redirect('/configurable-config/?error=表名和显示名称不能为空')
        
        # 生成表编码
        table_code = _generate_table_code()
        
        # 创建表配置
        table = ConfigurableTable.objects.create(
            table_code=table_code,
            table_name=table_name,
            display_name=display_name,
            description=description,
            is_active=True,
            sort_order=0
        )
        
        # 关联数据库配置
        if db_config_ids:
            from work_tools.models import DatabaseConfig
            for db_id in db_config_ids:
                try:
                    db_config = DatabaseConfig.objects.get(id=db_id)
                    table.database_configs.add(db_config)
                except DatabaseConfig.DoesNotExist:
                    logger.warning(f"[配置管理] 数据库配置不存在: {db_id}")
        
        # 清除缓存
        _clear_configurable_cache()
        
        logger.info(f"[配置管理] 添加表配置成功: {table_code}")
        return redirect(f'/configurable-config/?table_id={table.id}&message=添加表配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 添加表配置失败: {e}")
        return redirect(f'/configurable-config/?error=添加表配置失败: {str(e)}')


@require_POST
def configurable_table_edit(request):
    """编辑表配置"""
    try:
        table_id = request.POST.get('table_id')
        table_name = request.POST.get('table_name', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        description = request.POST.get('description', '').strip()
        db_config_ids = request.POST.getlist('db_configs')  # 获取选中的数据库配置
        
        if not table_name or not display_name:
            return redirect(f'/configurable-config/?table_id={table_id}&error=表名和显示名称不能为空')
        
        table = get_object_or_404(ConfigurableTable, id=table_id)
        table.table_name = table_name
        table.display_name = display_name
        table.description = description
        table.save()
        
        # 更新数据库配置关联
        table.database_configs.clear()
        if db_config_ids:
            from work_tools.models import DatabaseConfig
            for db_id in db_config_ids:
                try:
                    db_config = DatabaseConfig.objects.get(id=db_id)
                    table.database_configs.add(db_config)
                except DatabaseConfig.DoesNotExist:
                    logger.warning(f"[配置管理] 数据库配置不存在: {db_id}")
        
        # 清除缓存
        _clear_configurable_cache(table.table_code)
        
        logger.info(f"[配置管理] 编辑表配置成功: {table.table_code}")
        return redirect(f'/configurable-config/?table_id={table_id}&message=编辑表配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 编辑表配置失败: {e}")
        return redirect(f'/configurable-config/?error=编辑表配置失败: {str(e)}')


@require_POST
def configurable_table_toggle(request):
    """启用/禁用表配置"""
    try:
        table_id = request.POST.get('table_id')
        table = get_object_or_404(ConfigurableTable, id=table_id)
        
        table.is_active = not table.is_active
        table.save()
        
        # 清除缓存
        _clear_configurable_cache(table.table_code)
        
        status = '启用' if table.is_active else '禁用'
        logger.info(f"[配置管理] {status}表配置: {table.table_code}")
        return redirect(f'/configurable-config/?table_id={table_id}&message={status}表配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 切换表配置状态失败: {e}")
        return redirect(f'/configurable-config/?error=操作失败: {str(e)}')


@require_POST
def configurable_table_delete(request):
    """删除表配置"""
    try:
        table_id = request.POST.get('table_id')
        table = get_object_or_404(ConfigurableTable, id=table_id)
        table_code = table.table_code
        table_name = table.display_name
        
        # 删除表配置（会级联删除关联的字段配置）
        table.delete()
        
        # 清除缓存
        _clear_configurable_cache(table_code)
        
        logger.info(f"[配置管理] 删除表配置成功: {table_code} ({table_name})")
        return redirect('/configurable-config/?message=删除表配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 删除表配置失败: {e}")
        return redirect(f'/configurable-config/?table_id={table_id}&error=删除失败: {str(e)}')


@require_POST
def configurable_field_add(request):
    """添加字段配置"""
    try:
        table_id = request.POST.get('table_id')
        field_type = request.POST.get('field_type', '').strip()
        field_name = request.POST.get('field_name', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        data_type = request.POST.get('data_type', '').strip()
        is_required = request.POST.get('is_required') == 'on'
        is_nullable = request.POST.get('is_nullable') == 'on'
        sql_file_name = request.POST.get('sql_file_name', '').strip()
        max_length = request.POST.get('max_length', '').strip()
        default_value = request.POST.get('default_value', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        dropdown_group_id = request.POST.get('dropdown_group', '').strip()
        
        if not field_name or not display_name or not data_type:
            return redirect(f'/configurable-config/?table_id={table_id}&error=字段名、显示名称和数据类型不能为空')
        
        table = get_object_or_404(ConfigurableTable, id=table_id)
        
        # 检查字段名是否重复
        if ConfigurableField.objects.filter(table=table, field_name=field_name).exists():
            return redirect(f'/configurable-config/?table_id={table_id}&error=字段名已存在')
        
        # 如果是下拉框类型，验证下拉框分组是否选择
        dropdown_group = None
        if data_type == 'dropdown':
            if not dropdown_group_id:
                return redirect(f'/configurable-config/?table_id={table_id}&error=下拉框类型必须选择数据源分组')
            dropdown_group = get_object_or_404(DropdownGroup, id=dropdown_group_id)
        
        ConfigurableField.objects.create(
            table=table,
            field_type=field_type,
            field_name=field_name,
            display_name=display_name,
            data_type=data_type,
            is_required=is_required,
            is_nullable=is_nullable,
            sql_file_name=sql_file_name,
            max_length=int(max_length) if max_length else None,
            default_value=default_value,
            sort_order=int(sort_order),
            dropdown_group=dropdown_group,
            is_active=True
        )
        
        # 清除缓存
        _clear_configurable_cache(table.table_code)
        
        logger.info(f"[配置管理] 添加字段配置成功: {table.table_code}/{field_name}")
        return redirect(f'/configurable-config/?table_id={table_id}&message=添加字段配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 添加字段配置失败: {e}")
        return redirect(f'/configurable-config/?table_id={table_id}&error=添加字段配置失败: {str(e)}')


@require_POST
def configurable_field_edit(request):
    """编辑字段配置"""
    try:
        field_id = request.POST.get('field_id')
        field_name = request.POST.get('field_name', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        data_type = request.POST.get('data_type', '').strip()
        is_required = request.POST.get('is_required') == 'on'
        is_nullable = request.POST.get('is_nullable') == 'on'
        sql_file_name = request.POST.get('sql_file_name', '').strip()
        max_length = request.POST.get('max_length', '').strip()
        default_value = request.POST.get('default_value', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        dropdown_group_id = request.POST.get('dropdown_group', '').strip()
        
        if not field_name or not display_name or not data_type:
            return redirect(f'/configurable-config/?error=字段名、显示名称和数据类型不能为空')
        
        field = get_object_or_404(ConfigurableField, id=field_id)
        
        # 如果修改了字段名，检查新字段名是否与同表其他字段重复
        if field_name != field.field_name:
            if ConfigurableField.objects.filter(
                table=field.table, 
                field_name=field_name
            ).exclude(id=field_id).exists():
                return redirect(f'/configurable-config/?table_id={field.table.id}&error=字段名已存在')
            field.field_name = field_name
        
        # 如果是下拉框类型，验证下拉框分组是否选择
        if data_type == 'dropdown':
            if not dropdown_group_id:
                return redirect(f'/configurable-config/?table_id={field.table.id}&error=下拉框类型必须选择数据源分组')
            field.dropdown_group = get_object_or_404(DropdownGroup, id=dropdown_group_id)
        else:
            field.dropdown_group = None
        
        field.display_name = display_name
        field.data_type = data_type
        field.is_required = is_required
        field.is_nullable = is_nullable
        field.sql_file_name = sql_file_name
        field.max_length = int(max_length) if max_length else None
        field.default_value = default_value
        field.sort_order = int(sort_order)
        field.save()
        
        # 清除缓存
        _clear_configurable_cache(field.table.table_code)
        
        logger.info(f"[配置管理] 编辑字段配置成功: {field.table.table_code}/{field.field_name}")
        return redirect(f'/configurable-config/?table_id={field.table.id}&message=编辑字段配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 编辑字段配置失败: {e}")
        return redirect(f'/configurable-config/?error=编辑字段配置失败: {str(e)}')


@require_POST
def configurable_field_delete(request):
    """删除字段配置"""
    try:
        field_id = request.POST.get('field_id')
        field = get_object_or_404(ConfigurableField, id=field_id)
        
        table_id = field.table.id
        table_code = field.table.table_code
        field_name = field.field_name
        
        field.delete()
        
        # 清除缓存
        _clear_configurable_cache(table_code)
        
        logger.info(f"[配置管理] 删除字段配置成功: {table_code}/{field_name}")
        return redirect(f'/configurable-config/?table_id={table_id}&message=删除字段配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 删除字段配置失败: {e}")
        return redirect(f'/configurable-config/?error=删除字段配置失败: {str(e)}')


@require_POST
def configurable_field_toggle(request):
    """启用/禁用字段配置"""
    try:
        field_id = request.POST.get('field_id')
        field = get_object_or_404(ConfigurableField, id=field_id)
        
        field.is_active = not field.is_active
        field.save()
        
        # 清除缓存
        _clear_configurable_cache(field.table.table_code)
        
        status = '启用' if field.is_active else '禁用'
        logger.info(f"[配置管理] {status}字段配置: {field.table.table_code}/{field.field_name}")
        return redirect(f'/configurable-config/?table_id={field.table.id}&message={status}字段配置成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 切换字段配置状态失败: {e}")
        return redirect(f'/configurable-config/?error=操作失败: {str(e)}')


def _clear_configurable_cache(table_code=None):
    """清除可配置表缓存"""
    cache.delete('configurable_tables')
    # 清除导航缓存，确保菜单更新
    cache.delete('sidebar_groups')
    if table_code:
        cache.delete(f'configurable_fields_{table_code}')
        cache.delete(f'configurable_table_{table_code}')
        logger.info(f"[缓存清理] 已清除表配置 {table_code} 的缓存")
    else:
        # 清除所有表的字段配置缓存
        for table in ConfigurableTable.objects.all():
            cache.delete(f'configurable_fields_{table.table_code}')
            cache.delete(f'configurable_table_{table.table_code}')
        logger.info("[缓存清理] 已清除所有可配置表缓存")


def _generate_table_code():
    """生成唯一的表编码"""
    import random
    from datetime import datetime
    
    while True:
        # 格式: tbl_YYYYMMDDHHmmss_RRR
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_num = random.randint(100, 999)
        table_code = f'tbl_{timestamp}_{random_num}'
        
        # 检查是否重复
        if not ConfigurableTable.objects.filter(table_code=table_code).exists():
            return table_code


__all__ = [
    'configurable_config_view',
    'configurable_table_add',
    'configurable_table_edit',
    'configurable_table_toggle',
    'configurable_table_delete',
    'configurable_field_add',
    'configurable_field_edit',
    'configurable_field_delete',
    'configurable_field_toggle',
]
