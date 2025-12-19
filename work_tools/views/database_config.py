"""数据库配置管理视图"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from ..models import DatabaseConfig
from ..navigation import get_sidebar_groups

logger = logging.getLogger('work_tools.view')


def database_config_view(request):
    """数据库配置管理主页面"""
    try:
        # 获取所有数据库配置
        db_configs = DatabaseConfig.objects.all().order_by('sort_order', 'config_code')
        
        # 获取操作消息
        message = request.GET.get('message', '')
        error = request.GET.get('error', '')
        
        return render(request, 'database_config.html', {
            'db_configs': db_configs,
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'database_config',
            'message': message,
            'error': error,
        })
    except Exception as e:
        logger.error(f"[数据库配置] 加载页面失败: {e}")
        return render(request, 'database_config.html', {
            'db_configs': [],
            'sidebar_groups': get_sidebar_groups(),
            'active_menu': 'database_config',
            'error': f'加载失败: {str(e)}',
        })


@require_POST
def database_config_add(request):
    """添加数据库配置"""
    try:
        config_name = request.POST.get('config_name', '').strip()
        db_type = request.POST.get('db_type', 'oracle').strip()
        db_host = request.POST.get('db_host', '').strip()
        db_port = request.POST.get('db_port', '').strip()
        db_name = request.POST.get('db_name', '').strip()
        db_user = request.POST.get('db_user', '').strip()
        db_password = request.POST.get('db_password', '').strip()
        config_code = request.POST.get('config_code', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        
        # 如果没有提供config_code，自动生成
        if not config_code:
            import re
            import time
            # 从配置名称生成编码
            config_code = re.sub(r'[^a-zA-Z0-9_]', '_', config_name.lower())
            if not config_code:
                config_code = f'db_config_{int(time.time())}'
        
        # 验证输入
        if not config_name or not db_host or not db_name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': '配置名称、数据库地址和库名不能为空'})
            return redirect('/database-config/?error=配置名称、数据库地址和库名不能为空')
        
        # 验证编码格式（只允许字母、数字、下划线）
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', config_code):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': '配置编码只能包含字母、数字、下划线'})
            return redirect('/database-config/?error=配置编码只能包含字母、数字、下划线')
        
        # 创建配置
        db_config = DatabaseConfig.objects.create(
            config_code=config_code,
            config_name=config_name,
            db_type=db_type,
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            sort_order=int(sort_order),
            is_active=True
        )
        
        logger.info(f"[数据库配置] 添加配置成功: {config_code}")
        
        # 如果是AJAX请求，返回JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'db_config_id': db_config.id,
                'config_name': db_config.config_name,
                'db_host': db_config.db_host,
                'db_name': db_config.db_name
            })
        
        return redirect('/database-config/?message=添加配置成功')
        
    except Exception as e:
        logger.error(f"[数据库配置] 添加配置失败: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        return redirect(f'/database-config/?error=添加配置失败: {str(e)}')


@require_POST
def database_config_edit(request):
    """编辑数据库配置"""
    try:
        config_id = request.POST.get('config_id')
        config_name = request.POST.get('config_name', '').strip()
        db_host = request.POST.get('db_host', '').strip()
        db_name = request.POST.get('db_name', '').strip()
        sort_order = request.POST.get('sort_order', '0')
        
        if not config_name or not db_host or not db_name:
            return redirect(f'/database-config/?error=配置名称、数据库地址和库名不能为空')
        
        db_config = get_object_or_404(DatabaseConfig, id=config_id)
        db_config.config_name = config_name
        db_config.db_host = db_host
        db_config.db_name = db_name
        db_config.sort_order = int(sort_order)
        db_config.save()
        
        logger.info(f"[数据库配置] 编辑配置成功: {db_config.config_code}")
        return redirect('/database-config/?message=编辑配置成功')
        
    except Exception as e:
        logger.error(f"[数据库配置] 编辑配置失败: {e}")
        return redirect(f'/database-config/?error=编辑配置失败: {str(e)}')


@require_POST
def database_config_toggle(request):
    """启用/禁用数据库配置"""
    try:
        config_id = request.POST.get('config_id')
        db_config = get_object_or_404(DatabaseConfig, id=config_id)
        
        db_config.is_active = not db_config.is_active
        db_config.save()
        
        status = '启用' if db_config.is_active else '禁用'
        logger.info(f"[数据库配置] {status}配置: {db_config.config_code}")
        return redirect(f'/database-config/?message={status}配置成功')
        
    except Exception as e:
        logger.error(f"[数据库配置] 切换配置状态失败: {e}")
        return redirect(f'/database-config/?error=操作失败: {str(e)}')


@require_POST
def database_config_delete(request):
    """删除数据库配置"""
    try:
        config_id = request.POST.get('config_id')
        db_config = get_object_or_404(DatabaseConfig, id=config_id)
        
        config_code = db_config.config_code
        db_config.delete()
        
        logger.info(f"[数据库配置] 删除配置成功: {config_code}")
        return redirect('/database-config/?message=删除配置成功')
        
    except Exception as e:
        logger.error(f"[数据库配置] 删除配置失败: {e}")
        return redirect(f'/database-config/?error=删除配置失败: {str(e)}')


__all__ = [
    'database_config_view',
    'database_config_add',
    'database_config_edit',
    'database_config_toggle',
    'database_config_delete',
]
