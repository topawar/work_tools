"""系统配置模块"""
import os
import logging
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings

from ..config import get_config, set_config, get_module_names
from ..navigation import get_sidebar_groups

logger = logging.getLogger('work_tools.view')


def system_config_view(request):
    """系统配置视图"""
    saved = False
    error = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            mods = cfg.get('MERGE_MODULES', {})
            
            # 动态获取所有模块名称，确保与DEFAULT一致
            names = get_module_names()
            
            logger.info(f"[配置保存] 开始保存SQL合并配置")
            logger.debug(f"[配置保存] 当前配置: {mods}")
            
            # 记录变更
            changes = []
            
            for n in names:
                old_val = mods.get(n, True)
                new_val = (request.POST.get(f'mod_{n}') == 'on')
                mods[n] = new_val
                if old_val != new_val:
                    changes.append(f"{n}: {old_val} -> {new_val}")
                    logger.info(f"[配置保存] {n}: {old_val} -> {new_val}")
            
            cfg['MERGE_MODULES'] = mods
            
            # 保存前日志
            logger.info(f"[配置保存] 共{len(changes)}项变更")
            if changes:
                logger.info(f"[配置保存] 变更内容: {', '.join(changes)}")
            
            # 保存配置
            set_config(cfg)
            saved = True
            logger.info(f"[配置保存] 配置保存成功")
            
            # 验证保存结果
            verify_cfg = get_config()
            verify_mods = verify_cfg.get('MERGE_MODULES', {})
            
            # 检查每个模块是否正确保存
            verify_failed = []
            for n in names:
                expected = mods.get(n)
                actual = verify_mods.get(n)
                if expected != actual:
                    verify_failed.append(f"{n}(预期:{expected}, 实际:{actual})")
            
            if verify_failed:
                error = f"配置保存验证失败: {', '.join(verify_failed)}"
                logger.error(f"[配置保存] {error}")
                saved = False
            else:
                logger.debug(f"[配置保存] 验证成功：所有配置项已正确保存")
            
            # 重定向到GET请求以显示成功消息
            if saved:
                return redirect('/system/config/?saved=1')
        except Exception as e:
            error = str(e)
            logger.error(f"[配置保存] 保存失败: {error}", exc_info=True)
    
    # GET请求，检查是否有saved参数
    if request.GET.get('saved') == '1':
        saved = True
    
    cfg = get_config()
    logger.debug(f"[配置加载] 当前配置: {cfg.get('MERGE_MODULES', {})}")
    
    return render(request, 'system_config.html', {
        'cfg': cfg,
        'active_menu': 'system_config',
        'sidebar_groups': get_sidebar_groups(),
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


__all__ = ['system_config_view', 'download_sql', 'file_path_config_view', 'cleanup_config_view', 'select_folder_api', 'cleanup_now_view']


def _validate_path(path):
    """
    验证路径有效性
    
    Returns:
        dict: {'valid': bool, 'error': str, 'warning': str}
    """
    if not path:
        return {'valid': False, 'error': '路径不能为空', 'warning': ''}
    
    # 检查是否为绝对路径
    if not os.path.isabs(path):
        return {'valid': False, 'error': '请输入有效的绝对路径', 'warning': ''}
    
    # 检查路径是否存在
    if not os.path.exists(path):
        # 尝试创建目录
        try:
            os.makedirs(path, exist_ok=True)
            return {'valid': True, 'error': '', 'warning': '路径不存在，已自动创建'}
        except Exception as e:
            return {'valid': False, 'error': f'无法创建目录: {str(e)}', 'warning': ''}
    
    # 检查是否有写权限
    if not os.access(path, os.W_OK):
        return {'valid': False, 'error': '路径无写入权限，请选择其他位置', 'warning': ''}
    
    return {'valid': True, 'error': '', 'warning': ''}


def cleanup_now_view(request):
    """
    立即执行清理任务的视图
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # 捕获命令输出
        out = StringIO()
        call_command('cleanup_temp_files', stdout=out, stderr=out)
        output = out.getvalue()
        
        # 解析输出获取统计信息
        # 简单返回成功信息
        logger.info(f"[清理任务] 手动触发清理任务成功")
        
        return JsonResponse({
            'success': True,
            'message': '清理任务执行成功',
            'output': output
        })
        
    except Exception as e:
        logger.error(f"[清理任务] 手动触发清理失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'清理失败: {str(e)}'
        })


def file_path_config_view(request):
    """文件路径配置视图"""
    saved = False
    error = None
    warning = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            
            # 保存文件路径配置
            sql_output_path = request.POST.get('sql_output_path', '').strip()
            if sql_output_path:
                # 验证路径
                validation = _validate_path(sql_output_path)
                if not validation['valid']:
                    error = validation['error']
                    raise ValueError(validation['error'])
                
                if validation['warning']:
                    warning = validation['warning']
                
                cfg['SQL_OUTPUT_BASE_PATH'] = sql_output_path
                logger.info(f"[路径配置] SQL输出路径: {sql_output_path}")
            
            sql_output_mode = request.POST.get('sql_output_mode', 'hierarchical')
            cfg['SQL_OUTPUT_MODE'] = sql_output_mode
            logger.info(f"[路径配置] 路径模式: {sql_output_mode}")
            
            sql_date_format = request.POST.get('sql_date_format', '%Y%m/%d')
            cfg['SQL_OUTPUT_DATE_FORMAT'] = sql_date_format
            logger.info(f"[路径配置] 日期格式: {sql_date_format}")
            
            set_config(cfg)
            saved = True
            logger.info(f"[路径配置] 配置保存成功")
            
            return redirect('/system/file-path/?saved=1')
        except Exception as e:
            error = str(e)
            logger.error(f"[路径配置] 保存失败: {error}")
    
    if request.GET.get('saved') == '1':
        saved = True
    
    cfg = get_config()
    
    return render(request, 'file_path_config.html', {
        'cfg': cfg,
        'active_menu': 'file_path_config',
        'sidebar_groups': get_sidebar_groups(),
        'saved': saved,
        'error': error,
        'warning': warning,
    })


def cleanup_config_view(request):
    """临时文件清理配置视图"""
    saved = False
    error = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            
            # 保存临时文件清理配置
            cleanup_enabled = (request.POST.get('cleanup_enabled') == 'on')
            cfg['TEMP_FILE_CLEANUP_ENABLED'] = cleanup_enabled
            logger.info(f"[清理配置] 清理启用: {cleanup_enabled}")
            
            retention_hours = request.POST.get('retention_hours', '24')
            try:
                retention_hours = int(retention_hours)
                if retention_hours < 1 or retention_hours > 168:
                    raise ValueError("保留时长必须在1-168小时之间")
                cfg['TEMP_FILE_RETENTION_HOURS'] = retention_hours
                logger.info(f"[清理配置] 保留时长: {retention_hours}小时")
            except ValueError as e:
                error = str(e)
                raise
            
            set_config(cfg)
            saved = True
            logger.info(f"[清理配置] 配置保存成功")
            
            return redirect('/system/cleanup/?saved=1')
        except Exception as e:
            error = str(e)
            logger.error(f"[清理配置] 保存失败: {error}")
    
    if request.GET.get('saved') == '1':
        saved = True
    
    cfg = get_config()
    
    return render(request, 'cleanup_config.html', {
        'cfg': cfg,
        'active_menu': 'cleanup_config',
        'sidebar_groups': get_sidebar_groups(),
        'saved': saved,
        'error': error,
    })


def select_folder_api(request):
    """
    文件夹选择API
    使用tkinter文件对话框选择文件夹
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # 创建tkinter根窗口（隐藏）
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # 打开文件夹选择对话框
        folder_path = filedialog.askdirectory(
            title='选择SQL文件输出目录',
            mustexist=False
        )
        
        root.destroy()
        
        if folder_path:
            logger.info(f"[文件夹选择] 用户选择了路径: {folder_path}")
            return JsonResponse({
                'success': True,
                'path': folder_path
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '用户取消选择'
            })
            
    except Exception as e:
        logger.error(f"[文件夹选择] 失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'打开文件夹选择对话框失败: {str(e)}'
        })
