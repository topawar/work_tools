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
                logger.warning(f"[配置加载] 未找到配置分组: {group_code}")
                return _get_fallback_options(group_code, include_empty, empty_label)
            
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
            logger.error(f"[配置加载] 加载配置分组 {group_code} 失败: {e}")
            return _get_fallback_options(group_code, include_empty, empty_label)
    
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


def _get_fallback_options(group_code, include_empty, empty_label):
    """
    回退方案：当数据库中没有配置数据时，使用硬编码的选项
    
    这是为了向后兼容和应急使用
    """
    from .forms import APPR_STATE_CHOICES, BID_STATUS_CHOICES
    
    fallback_map = {
        'contract_status': APPR_STATE_CHOICES,
        'bid_status': BID_STATUS_CHOICES,
        'report_choice': [
            ('yes', '是（报送）'),
            ('no', '否（不报送）'),
        ],
        'importance_level': [
            ('0', '一般准入备案类 0'),
            ('1', '一般自行管理类 1'),
            ('4', '一般 4'),
            ('3', '核心 3'),
            ('2', '重要 2'),
        ],
    }
    
    options = fallback_map.get(group_code, [])
    logger.warning(f"[配置加载] 使用硬编码回退选项: {group_code}")
    
    if not include_empty and options and options[0][0] == '':
        return options[1:]
    elif include_empty and (not options or options[0][0] != ''):
        return [('', empty_label)] + options
    
    return options


__all__ = ['get_dropdown_options', 'clear_dropdown_cache']
