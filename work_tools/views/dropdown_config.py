"""下拉框配置管理视图"""
import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import DropdownGroup, DropdownOption
from ..navigation import get_sidebar_groups
from ..dropdown_utils import clear_dropdown_cache

logger = logging.getLogger('work_tools.view')


def dropdown_config_view(request):
    """配置管理主页面"""
    try:
        # 获取所有配置分组
        groups = DropdownGroup.objects.all().order_by('group_code')
        
        # 获取当前选中的分组
        selected_group_id = request.GET.get('group_id')
        if selected_group_id:
            selected_group = get_object_or_404(DropdownGroup, id=selected_group_id)
        elif groups.exists():
            selected_group = groups.first()
        else:
            selected_group = None
        
        # 获取当前分组的配置项
        options = []
        if selected_group:
            options = DropdownOption.objects.filter(
                group=selected_group
            ).order_by('sort_order', 'option_code')
        
        # 获取操作消息
        message = request.GET.get('message', '')
        error = request.GET.get('error', '')
        
        return render(request, 'dropdown_config.html', {
            'groups': groups,
            'selected_group': selected_group,
            'options': options,
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'dropdown_config',
            'message': message,
            'error': error,
        })
    except Exception as e:
        logger.error(f"[配置管理] 加载页面失败: {e}")
        return render(request, 'dropdown_config.html', {
            'groups': [],
            'selected_group': None,
            'options': [],
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'dropdown_config',
            'error': f'加载失败: {str(e)}',
        })


@require_POST
def dropdown_group_add(request):
    """添加配置分组"""
    try:
        group_name = request.POST.get('group_name', '').strip()
        description = request.POST.get('description', '').strip()
        
        # 验证输入
        if not group_name:
            return redirect(f'/dropdown-config/?error=分组名称不能为空')
        
        # 生成分组编码
        group_code = _generate_group_code()
        
        # 创建分组
        group = DropdownGroup.objects.create(
            group_code=group_code,
            group_name=group_name,
            description=description,
            is_active=True
        )
        
        logger.info(f"[配置管理] 添加分组成功: {group_code}")
        return redirect(f'/dropdown-config/?group_id={group.id}&message=添加分组成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 添加分组失败: {e}")
        return redirect(f'/dropdown-config/?error=添加分组失败: {str(e)}')


@require_POST
def dropdown_group_edit(request):
    """编辑配置分组"""
    try:
        group_id = request.POST.get('group_id')
        group_name = request.POST.get('group_name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not group_name:
            return redirect(f'/dropdown-config/?group_id={group_id}&error=分组名称不能为空')
        
        group = get_object_or_404(DropdownGroup, id=group_id)
        group.group_name = group_name
        group.description = description
        group.save()
        
        logger.info(f"[配置管理] 编辑分组成功: {group.group_code}")
        return redirect(f'/dropdown-config/?group_id={group_id}&message=编辑分组成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 编辑分组失败: {e}")
        return redirect(f'/dropdown-config/?error=编辑分组失败: {str(e)}')


@require_POST
def dropdown_group_toggle(request):
    """启用/禁用分组"""
    try:
        group_id = request.POST.get('group_id')
        group = get_object_or_404(DropdownGroup, id=group_id)
        
        group.is_active = not group.is_active
        group.save()
        
        # 清除缓存
        clear_dropdown_cache(group.group_code)
        
        status = '启用' if group.is_active else '禁用'
        logger.info(f"[配置管理] {status}分组: {group.group_code}")
        return redirect(f'/dropdown-config/?group_id={group_id}&message={status}分组成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 切换分组状态失败: {e}")
        return redirect(f'/dropdown-config/?error=操作失败: {str(e)}')


@require_POST
def dropdown_item_add(request):
    """添加配置项"""
    try:
        group_id = request.POST.get('group_id')
        option_code = request.POST.get('option_code', '').strip()
        option_label = request.POST.get('option_label', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        remark = request.POST.get('remark', '').strip()
        
        if not option_label:
            return redirect(f'/dropdown-config/?group_id={group_id}&error=选项标签不能为空')
        
        group = get_object_or_404(DropdownGroup, id=group_id)
        
        # 检查编码是否重复
        if DropdownOption.objects.filter(group=group, option_code=option_code).exists():
            return redirect(f'/dropdown-config/?group_id={group_id}&error=选项编码已存在')
        
        DropdownOption.objects.create(
            group=group,
            option_code=option_code,
            option_label=option_label,
            sort_order=int(sort_order),
            remark=remark,
            is_active=True,
            is_system=False
        )
        
        # 清除缓存
        clear_dropdown_cache(group.group_code)
        
        logger.info(f"[配置管理] 添加配置项成功: {group.group_code}/{option_code}")
        return redirect(f'/dropdown-config/?group_id={group_id}&message=添加配置项成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 添加配置项失败: {e}")
        return redirect(f'/dropdown-config/?group_id={group_id}&error=添加配置项失败: {str(e)}')


@require_POST
def dropdown_item_edit(request):
    """编辑配置项"""
    try:
        item_id = request.POST.get('item_id')
        option_code = request.POST.get('option_code', '').strip()
        option_label = request.POST.get('option_label', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        remark = request.POST.get('remark', '').strip()
        
        if not option_label:
            return redirect(f'/dropdown-config/?error=选项标签不能为空')
        
        option = get_object_or_404(DropdownOption, id=item_id)
        
        # 如果修改了编码，检查新编码是否与同组其他选项重复
        if option_code != option.option_code:
            if DropdownOption.objects.filter(
                group=option.group, 
                option_code=option_code
            ).exclude(id=item_id).exists():
                return redirect(f'/dropdown-config/?group_id={option.group.id}&error=选项编码已存在')
            option.option_code = option_code
        
        option.option_label = option_label
        option.sort_order = int(sort_order)
        option.remark = remark
        option.save()
        
        # 清除缓存
        clear_dropdown_cache(option.group.group_code)
        
        logger.info(f"[配置管理] 编辑配置项成功: {option.group.group_code}/{option.option_code}")
        return redirect(f'/dropdown-config/?group_id={option.group.id}&message=编辑配置项成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 编辑配置项失败: {e}")
        return redirect(f'/dropdown-config/?error=编辑配置项失败: {str(e)}')


@require_POST
def dropdown_item_delete(request):
    """删除配置项"""
    try:
        item_id = request.POST.get('item_id')
        option = get_object_or_404(DropdownOption, id=item_id)
        
        # 检查是否为系统内置项
        if option.is_system:
            return redirect(f'/dropdown-config/?group_id={option.group.id}&error=系统内置项不能删除')
        
        group_id = option.group.id
        group_code = option.group.group_code
        option_code = option.option_code
        
        option.delete()
        
        # 清除缓存
        clear_dropdown_cache(group_code)
        
        logger.info(f"[配置管理] 删除配置项成功: {group_code}/{option_code}")
        return redirect(f'/dropdown-config/?group_id={group_id}&message=删除配置项成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 删除配置项失败: {e}")
        return redirect(f'/dropdown-config/?error=删除配置项失败: {str(e)}')


@require_POST
def dropdown_item_toggle(request):
    """启用/禁用配置项"""
    try:
        item_id = request.POST.get('item_id')
        option = get_object_or_404(DropdownOption, id=item_id)
        
        option.is_active = not option.is_active
        option.save()
        
        # 清除缓存
        clear_dropdown_cache(option.group.group_code)
        
        status = '启用' if option.is_active else '禁用'
        logger.info(f"[配置管理] {status}配置项: {option.group.group_code}/{option.option_code}")
        return redirect(f'/dropdown-config/?group_id={option.group.id}&message={status}配置项成功')
        
    except Exception as e:
        logger.error(f"[配置管理] 切换配置项状态失败: {e}")
        return redirect(f'/dropdown-config/?error=操作失败: {str(e)}')


def _generate_group_code():
    """生成唯一的分组编码"""
    import random
    from datetime import datetime
    
    while True:
        # 格式: grp_YYYYMMDDHHmmss_RRR
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_num = random.randint(100, 999)
        group_code = f'grp_{timestamp}_{random_num}'
        
        # 检查是否重复
        if not DropdownGroup.objects.filter(group_code=group_code).exists():
            return group_code


__all__ = [
    'dropdown_config_view',
    'dropdown_group_add',
    'dropdown_group_edit',
    'dropdown_group_toggle',
    'dropdown_item_add',
    'dropdown_item_edit',
    'dropdown_item_delete',
    'dropdown_item_toggle',
]
