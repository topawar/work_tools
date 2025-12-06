"""
基础工具函数模块
包含所有视图共用的基础函数
"""
import os
import re
from datetime import datetime
from ..models import OrgDetail


# SQL文件保存基础目录
SQL_BASE_DIR = r"D:\临时文件"


def save_sql_file(sql_content, prefix='sql', dynamic_id=None):
    """
    保存SQL内容到固定目录
    返回文件路径
    保存位置: D:\临时文件\{YYYYMM}\{DD}\{filename}.sql
    """
    now = datetime.now()
    year_month = now.strftime('%Y%m')
    day = now.strftime('%d')
    target_dir = os.path.join(SQL_BASE_DIR, year_month, day)
    os.makedirs(target_dir, exist_ok=True)

    if dynamic_id:
        filename = f'{dynamic_id}_{prefix}.sql'
    else:
        timestamp = now.strftime('%H%M%S')
        filename = f'{prefix}_{timestamp}.sql'

    filepath = os.path.join(target_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(sql_content)

    return filepath


def parse_ops_remark(remark):
    """解析操作备注,提取任务编号和描述"""
    if not isinstance(remark, str):
        return ''
    remark = remark.strip()
    if not remark:
        return ''
    # 匹配 #123 描述 https://xxx 格式
    m = re.search(r'#(\d+)\s+(.+?)(?:\s+`?https?://\S+`?)', remark)
    if m:
        desc = m.group(2).replace('`', '').strip()
        return f"{m.group(1)} {desc}".strip()
    # 匹配 ONES链接格式
    ones_m = re.search(
        r'https://ones\.cnsc-sh\.com/project/#/team/[^/]+/task/([^\s`]+)', remark)
    if ones_m:
        tid = ones_m.group(1)
        num_m = re.search(r'\d+', tid)
        num = num_m.group() if num_m else tid
        desc = remark.replace(ones_m.group(0), '').replace('`', '').strip()
        return f"{num} {desc}".strip()
    return remark


def extract_company_code(value):
    """从"名称-编码"格式中提取编码"""
    if not isinstance(value, str):
        return None
    s = value.strip()
    m = re.match(r"^(.*?)-(\w+)$", s)
    if m:
        return m.group(2)
    return None


def extract_company_name(value):
    """从"名称-编码"格式中提取名称,如果没有编码则返回原值"""
    if not isinstance(value, str):
        return None
    s = value.strip()
    m = re.match(r"^(.*?)-(\w+)$", s)
    if m:
        return m.group(1)
    return s


def _unique_code_by_name(name: str):
    """根据组织机构名称查询唯一的编码"""
    qs = OrgDetail.objects.filter(company_name__iexact=str(name).strip())
    if qs.count() == 1:
        obj = qs.first()
        return obj.company_code if obj and obj.company_code else None
    return None


def normalize_item_id(value):
    """规范化物资编码格式"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s


__all__ = [
    'parse_ops_remark',
    'extract_company_code',
    'extract_company_name',
    '_unique_code_by_name',
    'normalize_item_id',
    'save_sql_file',
    'SQL_BASE_DIR',
]
