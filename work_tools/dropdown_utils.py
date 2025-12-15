"""下拉框配置加载工具模块"""
from django.core.cache import cache
from django.db.models import Q
import logging

logger = logging.getLogger('work_tools.view')


def get_dropdown_options(group_code, include_empty=True, empty_label='请选择'):
    """
    根据分组编码获取下拉框选项列表
    
    Args:
        group_code: 配置分组编码
        include_empty: 是否包含空选项
        empty_label: 空选项的显示文本
        
    Returns:
        元组列表，格式为 [(选项编码, 选项标签), ...]
        如果配置不存在或未启用，返回空列表
    """
    # 尝试从缓存获取
    cache_key = f'dropdown_options_{group_code}'
    options = cache.get(cache_key)
    
    if options is None:
        # 缓存未命中，从数据库加载
        try:
            from .models import DropdownGroup, DropdownOption
            
            group = DropdownGroup.objects.filter(
                group_code=group_code,
                is_active=True
            ).first()
            
            if not group:
                logger.warning(f"[配置加载] 未找到或未启用配置分组: {group_code}，返回空列表")
                return []
            
            # 查询启用的配置项
            option_objs = DropdownOption.objects.filter(
                group=group,
                is_active=True
            ).order_by('sort_order', 'option_code')
            
            options = [(opt.option_code, opt.option_label) for opt in option_objs]
            
            # 存入缓存（30分钟）
            cache.set(cache_key, options, 30 * 60)
            logger.info(f"[配置加载] 成功加载配置分组 {group_code}，共 {len(options)} 项")
            
        except Exception as e:
            logger.error(f"[配置加载] 加载配置分组 {group_code} 失败: {e}，返回空列表")
            return []
    
    # 根据参数决定是否添加空选项
    if include_empty and (not options or options[0][0] != ''):
        options = [('', empty_label)] + options
    elif not include_empty and options and options[0][0] == '':
        options = options[1:]
    
    return options


def clear_dropdown_cache(group_code=None):
    """
    清除下拉框配置缓存
    
    Args:
        group_code: 配置分组编码，如果为None则清除所有缓存
    """
    if group_code:
        cache_key = f'dropdown_options_{group_code}'
        cache.delete(cache_key)
        logger.info(f"[缓存清理] 已清除配置分组 {group_code} 的缓存")
    else:
        # 清除所有下拉框配置缓存
        from .models import DropdownGroup
        for group in DropdownGroup.objects.all():
            cache_key = f'dropdown_options_{group.group_code}'
            cache.delete(cache_key)
        logger.info("[缓存清理] 已清除所有下拉框配置缓存")



__all__ = ['get_dropdown_options', 'clear_dropdown_cache']
