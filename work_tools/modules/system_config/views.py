"""系统配置模块视图"""
import os
import logging
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings

from work_tools.config import get_config, set_config, get_module_names
from work_tools.navigation import get_sidebar_groups

logger = logging.getLogger('work_tools.view')


def system_config_view(request):
    """系统配置视图"""
    saved = False
    error = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            mods = cfg.get('MERGE_MODULES', {})
            
            # 动态获取所有模块名称
            names = get_module_names()
            
            logger.info(f"[配置保存] 开始保存SQL合并配置")
            
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
            
            # 保存配置
            set_config(cfg)
            saved = True
            logger.info(f"[配置保存] 配置保存成功，共{len(changes)}项变更")
            
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
    
    return render(request, 'modules/system_config/system_config.html', {
        'cfg': cfg,
        'active_menu': 'system_config',
        'sidebar_groups': get_sidebar_groups(),
        'saved': saved,
        'error': error,
    })


def _validate_path(path):
    """验证路径有效性"""
    if not path:
        return {'valid': False, 'error': '路径不能为空', 'warning': ''}
    
    if not os.path.isabs(path):
        return {'valid': False, 'error': '请输入有效的绝对路径', 'warning': ''}
    
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            return {'valid': True, 'error': '', 'warning': '路径不存在，已自动创建'}
        except Exception as e:
            return {'valid': False, 'error': f'无法创建目录: {str(e)}', 'warning': ''}
    
    if not os.access(path, os.W_OK):
        return {'valid': False, 'error': '路径无写入权限，请选择其他位置', 'warning': ''}
    
    return {'valid': True, 'error': '', 'warning': ''}


def file_path_config_view(request):
    """文件路径配置视图"""
    saved = False
    error = None
    warning = None
    
    if request.method == 'POST':
        try:
            cfg = get_config()
            
            sql_output_path = request.POST.get('sql_output_path', '').strip()
            if sql_output_path:
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
            
            sql_date_format = request.POST.get('sql_date_format', '%Y%m/%d')
            cfg['SQL_OUTPUT_DATE_FORMAT'] = sql_date_format
            
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
    
    return render(request, 'modules/system_config/file_path_config.html', {
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
            
            cleanup_enabled = (request.POST.get('cleanup_enabled') == 'on')
            cfg['TEMP_FILE_CLEANUP_ENABLED'] = cleanup_enabled
            
            retention_hours = request.POST.get('retention_hours', '24')
            try:
                retention_hours = int(retention_hours)
                if retention_hours < 1 or retention_hours > 168:
                    raise ValueError("保留时长必须在1-168小时之间")
                cfg['TEMP_FILE_RETENTION_HOURS'] = retention_hours
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
    
    return render(request, 'modules/system_config/cleanup_config.html', {
        'cfg': cfg,
        'active_menu': 'cleanup_config',
        'sidebar_groups': get_sidebar_groups(),
        'saved': saved,
        'error': error,
    })


def cleanup_now_view(request):
    """立即执行清理任务"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('cleanup_temp_files', stdout=out, stderr=out)
        output = out.getvalue()
        
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


def select_folder_api(request):
    """文件夹选择API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '仅支持POST请求'})
    
    folder_path = None
    
    try:
        import ctypes
        from ctypes import wintypes
        
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        
        ole32.CoInitialize(None)
        
        class BROWSEINFO(ctypes.Structure):
            _fields_ = [
                ("hwndOwner", wintypes.HWND),
                ("pidlRoot", ctypes.c_void_p),
                ("pszDisplayName", ctypes.c_wchar_p),
                ("lpszTitle", ctypes.c_wchar_p),
                ("ulFlags", ctypes.c_uint),
                ("lpfn", ctypes.c_void_p),
                ("lParam", ctypes.c_long),
                ("iImage", ctypes.c_int),
            ]
        
        BIF_RETURNONLYFSDIRS = 0x0001
        BIF_NEWDIALOGSTYLE = 0x0040
        
        bi = BROWSEINFO()
        bi.hwndOwner = None
        bi.pidlRoot = None
        bi.pszDisplayName = ctypes.create_unicode_buffer(260)
        bi.lpszTitle = "选择SQL文件输出目录"
        bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE
        bi.lpfn = None
        bi.lParam = 0
        bi.iImage = 0
        
        pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
        
        if pidl:
            path_buffer = ctypes.create_unicode_buffer(260)
            shell32.SHGetPathFromIDListW(pidl, path_buffer)
            ole32.CoTaskMemFree(pidl)
            folder_path = path_buffer.value
        
        ole32.CoUninitialize()
        
    except Exception as e:
        logger.warning(f"[文件夹选择] Windows原生对话框失败: {e}")
        
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            folder_path = filedialog.askdirectory(
                title='选择SQL文件输出目录',
                mustexist=False
            )
            
            root.destroy()
            
        except Exception as tk_error:
            logger.error(f"[文件夹选择] tkinter也失败: {tk_error}")
            return JsonResponse({
                'success': False,
                'error': f'打开文件夹选择对话框失败，请手动输入路径'
            })
    
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


def download_sql(request, filename):
    """下载SQL文件"""
    file_path = os.path.join(settings.BASE_DIR, 'temp_downloads', filename)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'),
                                as_attachment=True, filename=filename)
        return response
    else:
        return HttpResponse("文件不存在", status=404)


__all__ = [
    'system_config_view',
    'file_path_config_view',
    'cleanup_config_view',
    'select_folder_api',
    'cleanup_now_view',
    'download_sql'
]
