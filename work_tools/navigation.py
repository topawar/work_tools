SIDEBAR_GROUPS = [
    {
        'title': '合同',
        'items': [
            {'label': '明细单价修改', 'url_name': 'contract_price'},
            {'label': '物资编码修改', 'url_name': 'contract_item'},
            {'label': '合同预算修改', 'url_name': 'contract_budget'},
            {'label': '合同失效日期修改', 'url_name': 'enddate'},
            {'label': '适用清单修改', 'url_name': 'use_list_update'},
            {'label': '合同状态修改', 'url_name': 'appr_state_change'},
            {'label': '终止合同', 'url_name': 'contract_terminate'},
            {'label': '终止简化寻源合同', 'url_name': 'sourcing_terminate'},
        ],
    },
    {
        'title': '计划-寻源',
        'items': [
            {'label': '合同起草、签约单位修改', 'url_name': 'unit_change'},
            {'label': '是否报送国资委', 'url_name': 'gov_report'},
            {'label': '物项重要性修改', 'url_name': 'importance'},
            {'label': '浮动单价类型修改', 'url_name': 'price_type_update'},
            {'label': '核电ERP终止', 'url_name': 'erp_terminate'},
            {'label': '项目轮次', 'url_name': 'project_round'},
        ],
    },
    {
        'title': '数据导入',
        'items': [
            {'label': '组织机构导入', 'url_name': 'org_import'},
            {'label': '物资信息导入', 'url_name': 'item_import'},
        ],
    },
    {
        'title': '任务管理',
        'items': [
            {'label': '导入任务', 'url_name': 'job_list'},
        ],
    },
    {
        'title': '系统配置',
        'items': [
            {'label': 'SQL合并策略', 'url_name': 'system_config'},
        ],
    },
]
