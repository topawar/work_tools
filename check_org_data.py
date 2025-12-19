#!/usr/bin/env python
"""
组织机构数据检查脚本
用于诊断数据导入和查询问题
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_tools.settings')
django.setup()

from work_tools.models import OrgDetail
from django.db.models import Q

def check_duplicate_codes():
    """检查重复的company_code"""
    print("=== 检查重复的company_code ===")
    from django.db.models import Count
    duplicates = OrgDetail.objects.values('company_code').annotate(
        count=Count('company_code')
    ).filter(count__gt=1, company_code__isnull=False)
    
    for dup in duplicates:
        code = dup['company_code']
        count = dup['count']
        print(f"编码 {code} 有 {count} 条记录:")
        records = OrgDetail.objects.filter(company_code=code)
        for r in records:
            print(f"  - {r.company_name} (ID: {r.id})")
        print()

def check_zhonghe_records():
    """检查中核相关记录"""
    print("=== 检查中核相关记录 ===")
    records = OrgDetail.objects.filter(
        Q(company_name__icontains='中核') & Q(company_name__icontains='供应链')
    ).order_by('company_name')
    
    print(f"找到 {records.count()} 条中核供应链相关记录:")
    for r in records:
        print(f"  - {r.company_name} | {r.company_code or 'None'}")
    print()

def search_exact_match():
    """测试精确匹配"""
    print("=== 测试精确匹配 ===")
    target = "中核（上海）供应链管理有限公司"
    exact = OrgDetail.objects.filter(company_name=target)
    print(f"精确匹配 '{target}': {exact.count()} 条记录")
    for r in exact:
        print(f"  - {r.company_name} | {r.company_code or 'None'}")
    print()

def search_fuzzy_match():
    """测试模糊匹配"""
    print("=== 测试模糊匹配 ===")
    target = "中核（上海）供应链管理有限公司"
    fuzzy = OrgDetail.objects.filter(company_name__icontains=target)
    print(f"模糊匹配 '{target}': {fuzzy.count()} 条记录")
    for r in fuzzy:
        print(f"  - {r.company_name} | {r.company_code or 'None'}")
    print()

def check_missing_records():
    """检查可能缺失的记录"""
    print("=== 检查可能缺失的记录 ===")
    # 检查是否有西北分公司但没有总公司的情况
    branch_records = OrgDetail.objects.filter(company_name__icontains='西北分公司')
    print("西北分公司记录:")
    for r in branch_records:
        parent_name = r.company_name.replace('西北分公司', '')
        parent_exists = OrgDetail.objects.filter(company_name=parent_name).exists()
        print(f"  - {r.company_name} | 总公司存在: {parent_exists}")
    print()

if __name__ == '__main__':
    print("开始检查组织机构数据...")
    print("=" * 50)
    
    check_duplicate_codes()
    check_zhonghe_records()
    search_exact_match()
    search_fuzzy_match()
    check_missing_records()
    
    print("检查完成!")