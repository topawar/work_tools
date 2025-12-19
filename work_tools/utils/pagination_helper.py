"""分页和搜索辅助工具"""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q


def paginate_queryset(queryset, page, per_page=10):
    """
    通用分页辅助函数
    
    Args:
        queryset: Django QuerySet 对象
        page: 页码（字符串或整数）
        per_page: 每页显示数量，默认10条
    
    Returns:
        Page 对象，包含当前页的数据和分页信息
    """
    paginator = Paginator(queryset, per_page)
    
    try:
        page_obj = paginator.get_page(page)
    except (EmptyPage, PageNotAnInteger):
        # 如果页码无效，返回第一页
        page_obj = paginator.get_page(1)
    
    return page_obj


def filter_by_search(queryset, search_query, fields):
    """
    通用搜索过滤辅助函数
    
    Args:
        queryset: Django QuerySet 对象
        search_query: 搜索关键词
        fields: 要搜索的字段列表，例如 ['name', 'code']
    
    Returns:
        过滤后的 QuerySet 对象
    """
    if not search_query or not search_query.strip():
        return queryset
    
    # 构建 Q 对象进行多字段模糊搜索
    q_objects = Q()
    for field in fields:
        q_objects |= Q(**{f'{field}__icontains': search_query})
    
    return queryset.filter(q_objects)


__all__ = ['paginate_queryset', 'filter_by_search']
