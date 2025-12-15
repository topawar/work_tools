from pypinyin import lazy_pinyin, Style
from django.core.cache import cache

# 原始导航数据结构
_SIDEBAR_GROUPS_RAW = [
    {
        'title': '合同',
        'icon': 'bi-file-text',
        'items': [
            {'label': '明细单价修改', 'url_name': 'contract_price', 'icon': 'bi-currency-dollar'},
            {'label': '物资编码修改', 'url_name': 'contract_item', 'icon': 'bi-tag'},
            {'label': '合同预算修改', 'url_name': 'contract_budget', 'icon': 'bi-calculator'},
            {'label': '合同失效日期修改', 'url_name': 'enddate', 'icon': 'bi-calendar-x'},
            {'label': '适用清单修改', 'url_name': 'use_list_update', 'icon': 'bi-list-ul'},
            {'label': '合同状态修改', 'url_name': 'appr_state_change', 'icon': 'bi-arrow-repeat'},
            {'label': '合同创建人修改', 'url_name': 'contract_creator_update', 'icon': 'bi-person-badge'},
            {'label': '终止合同', 'url_name': 'contract_terminate', 'icon': 'bi-x-circle'},
            {'label': '终止简化寻源合同', 'url_name': 'sourcing_terminate', 'icon': 'bi-x-square'},
        ],
    },
    {
        'title': '计划-寻源',
        'icon': 'bi-briefcase',
        'items': [
            {'label': '合同起草、签约单位修改', 'url_name': 'unit_change', 'icon': 'bi-building'},
            {'label': '是否报送国资委', 'url_name': 'gov_report', 'icon': 'bi-send'},
            {'label': '物项重要性修改', 'url_name': 'importance', 'icon': 'bi-star'},
            {'label': '浮动单价类型修改', 'url_name': 'price_type_update', 'icon': 'bi-graph-up-arrow'},
            {'label': '核电ERP终止', 'url_name': 'erp_terminate', 'icon': 'bi-power'},
            {'label': '项目轮次', 'url_name': 'project_round', 'icon': 'bi-arrow-clockwise'},
            {'label': '需求计划明细日期修改', 'url_name': 'plan_date_update', 'icon': 'bi-calendar-event'},
            {'label': '订单执行人修改', 'url_name': 'order_executor_update', 'icon': 'bi-person-badge'},
        ],
    },
    {
        'title': '数据导入',
        'icon': 'bi-database',
        'items': [
            {'label': '组织机构导入', 'url_name': 'org_import', 'icon': 'bi-diagram-3'},
            {'label': '用户组织机构导入', 'url_name': 'user_org_import', 'icon': 'bi-people'},
            {'label': '物资信息导入', 'url_name': 'item_import', 'icon': 'bi-box-seam'},
        ],
    },
    {
        'title': '任务管理',
        'icon': 'bi-list-check',
        'items': [
            {'label': '导入任务', 'url_name': 'job_list', 'icon': 'bi-cloud-upload'},
        ],
    },
    {
        'title': '系统配置',
        'icon': 'bi-gear',
        'items': [
            {'label': 'SQL合并策略', 'url_name': 'system_config', 'icon': 'bi-layers'},
            {'label': '文件路径配置', 'url_name': 'file_path_config', 'icon': 'bi-folder'},
            {'label': '临时文件清理', 'url_name': 'cleanup_config', 'icon': 'bi-trash'},
            {'label': '下拉框配置管理', 'url_name': 'dropdown_config', 'icon': 'bi-menu-button-wide'},
            {'label': '可配置表管理', 'url_name': 'configurable_config', 'icon': 'bi-sliders'},
            {'label': '数据库配置管理', 'url_name': 'database_config', 'icon': 'bi-server'},
        ],
    },
]


def _get_dynamic_configurable_items():
    """动态获取可配置表菜单项（带缓存）"""
    cache_key = 'configurable_tables'
    tables = cache.get(cache_key)
    
    if tables is None:
        try:
            from .models import ConfigurableTable
            tables = ConfigurableTable.objects.filter(is_active=True).order_by('sort_order', 'table_code')
            cache.set(cache_key, list(tables), 30 * 60)
        except Exception:
            tables = []
    
    items = []
    for table in tables:
        items.append({
            'label': table.display_name,
            'url_name': 'configurable_data',
            'url_kwargs': {'table_code': table.table_code},
            'icon': 'bi-pencil-square',
        })
    
    return items


def _generate_sidebar_groups_with_pinyin():
    """
    为导航数据添加拼音索引,用于前端搜索
    动态添加可配置表分组
    """
    groups_with_pinyin = []
    
    # 处理静态分组
    for group in _SIDEBAR_GROUPS_RAW:
        group_title = group['title']
        group_icon = group.get('icon', '')
        items_with_pinyin = []
        
        for item in group['items']:
            label = item['label']
            # 生成拼音全拼（小写，无分隔符）
            pinyin_full = ''.join(lazy_pinyin(label, style=Style.NORMAL))
            # 生成拼音首字母（小写）
            pinyin_abbr = ''.join(lazy_pinyin(label, style=Style.FIRST_LETTER))
            
            items_with_pinyin.append({
                'label': label,
                'url_name': item['url_name'],
                'url_kwargs': item.get('url_kwargs'),
                'icon': item.get('icon', ''),
                'pinyin_full': pinyin_full.lower(),
                'pinyin_abbr': pinyin_abbr.lower(),
                'group_name': group_title,
            })
        
        groups_with_pinyin.append({
            'title': group_title,
            'icon': group_icon,
            'items': items_with_pinyin,
            'open': group.get('open', False),
        })
    
    # 动态添加特殊模板分组
    dynamic_items = _get_dynamic_configurable_items()
    if dynamic_items:
        items_with_pinyin = []
        for item in dynamic_items:
            label = item['label']
            pinyin_full = ''.join(lazy_pinyin(label, style=Style.NORMAL))
            pinyin_abbr = ''.join(lazy_pinyin(label, style=Style.FIRST_LETTER))
            
            items_with_pinyin.append({
                'label': label,
                'url_name': item['url_name'],
                'url_kwargs': item.get('url_kwargs'),
                'icon': item.get('icon', ''),
                'pinyin_full': pinyin_full.lower(),
                'pinyin_abbr': pinyin_abbr.lower(),
                'group_name': '特殊模板',
            })
        
        groups_with_pinyin.append({
            'title': '特殊模板',
            'icon': 'bi-tools',
            'items': items_with_pinyin,
            'open': False,
        })
    
    return groups_with_pinyin


def get_sidebar_groups():
    """
    获取导航菜单数据（支持缓存）
    每次请求时调用此函数，从缓存获取或重新生成导航数据
    """
    cache_key = 'sidebar_groups'
    sidebar_groups = cache.get(cache_key)
    
    if sidebar_groups is None:
        sidebar_groups = _generate_sidebar_groups_with_pinyin()
        # 缓存30分钟
        cache.set(cache_key, sidebar_groups, 30 * 60)
    
    return sidebar_groups


# 为了保持向后兼容，保留 SIDEBAR_GROUPS 变量
# 但建议所有视图改为调用 get_sidebar_groups() 函数
SIDEBAR_GROUPS = get_sidebar_groups()
