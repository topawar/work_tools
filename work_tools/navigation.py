from pypinyin import lazy_pinyin, Style

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
        ],
    },
    {
        'title': '数据导入',
        'icon': 'bi-database',
        'items': [
            {'label': '组织机构导入', 'url_name': 'org_import', 'icon': 'bi-diagram-3'},
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
        ],
    },
]


def _generate_sidebar_groups_with_pinyin():
    """
    为导航数据添加拼音索引，用于前端搜索
    """
    groups_with_pinyin = []
    
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
    
    return groups_with_pinyin


# 导出带拼音索引的导航数据，供所有视图使用
SIDEBAR_GROUPS = _generate_sidebar_groups_with_pinyin()
