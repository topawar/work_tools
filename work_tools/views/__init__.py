"""
Views模块 - 将庞大的view.py拆分为多个功能模块
"""
from .base import *
from .contract_price import *
from .contract_item import *
from .contract_budget import *
from .contract_unit import *
from .use_list import *
from .enddate import *
from .importance import *
from .erp_terminate import *
from .price_type import *
from .gov_report import *
from .item_manage import *
from .org_api import *
from .job_manage import *
from .system_config import *
from .appr_state import *
from .contract_terminate import *
from .sourcing_terminate import *
from .project_round import *

__all__ = [
    # 基础工具函数
    'parse_ops_remark',
    'extract_company_code',
    'extract_company_name',

    # 合同单价修改
    'contract_price_view',
    'contract_detail_price_view',
    'download_contract_price_template',
    'download_price_template',  # 别名
    'parse_price_excel',
    'generate_price_sql_bulk',

    # 物资编码修改
    'contract_item_view',
    'download_contract_item_template',
    'contract_item_update_view',  # 别名
    'download_item_template',  # 别名

    # 合同预算修改
    'contract_budget_view',
    'contract_budget_update_view',  # 别名
    'download_budget_template',

    # 合同单位修改
    'unit_change_view',
    'download_unit_template',
    'org_search_api',

    # 失效日期修改
    'enddate_update_view',
    'download_enddate_template',

    # 适用清单修改
    'use_list_update_view',
    'download_use_list_template',

    # 物项重要性修改
    'importance_view',
    'importance_update_view',  # 别名
    'download_importance_template',

    # 政采云报告
    'gov_report_view',
    'download_gov_template',

    # ERP合同终止
    'erp_terminate_view',
    'download_erp_terminate_template',

    # 浮动单价类型
    'floating_price_type_view',
    'download_price_type_template',

    # 物资数据管理
    'item_import_view',
    'item_search_api',
    'item_detail_api',

    # 组织机构API
    'org_import_view',

    # 任务管理
    'job_list_view',
    'job_detail_view',
    'job_status_api',
    'job_delete_view',
    'job_fail_view',

    # 系统配置
    'system_config_view',
    'download_sql',

    # 合同状态修改
    'appr_state_change_view',
    'download_appr_state_template',

    # 终止合同
    'contract_terminate_view',
    'download_terminate_template',

    # 终止简化寻源合同
    'sourcing_terminate_view',
    'download_sourcing_terminate_template',

    # 项目轮次
    'project_round_view',
    'download_project_round_template',
]
