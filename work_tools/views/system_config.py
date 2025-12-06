"""系统配置模块"""
import os
import logging
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse
from django.conf import settings

from ..config import get_config, set_config
from ..navigation import SIDEBAR_GROUPS

logger = logging.getLogger('work_tools.view')


def system_config_view(request):
    """系统配置视图"""
    saved = False
    error = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            mods = cfg.get('MERGE_MODULES', {})
            names = ['price', 'item', 'unit', 'budget', 'gov',
                     'importance', 'enddate', 'erp', 'price_type', 'use_list', 'appr_state', 'contract_terminate', 'sourcing_terminate', 'project_round']
            
            logger.info(f"[配置保存] 开始保存SQL合并配置")
            for n in names:
                old_val = mods.get(n, True)
                new_val = (request.POST.get(f'mod_{n}') == 'on')
                mods[n] = new_val
                if old_val != new_val:
                    logger.info(f"[配置保存] {n}: {old_val} -> {new_val}")
            
            cfg['MERGE_MODULES'] = mods
            set_config(cfg)
            saved = True
            logger.info(f"[配置保存] 配置保存成功: {mods}")
            
            # 重定向到GET请求以显示成功消息
            return redirect('/system/config/?saved=1')
        except Exception as e:
            error = str(e)
            logger.error(f"[配置保存] 保存失败: {error}")
    
    # GET请求，检查是否有saved参数
    if request.GET.get('saved') == '1':
        saved = True
    
    cfg = get_config()
    logger.info(f"[配置加载] 当前配置: {cfg.get('MERGE_MODULES', {})}")
    
    return render(request, 'system_config.html', {
        'cfg': cfg,
        'active_menu': 'system_config',
        'sidebar_groups': SIDEBAR_GROUPS,
        'saved': saved,
        'error': error,
    })


def download_sql(request, filename):
    """下载SQL文件"""
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


__all__ = ['system_config_view', 'download_sql']
