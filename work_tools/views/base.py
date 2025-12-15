"""
基础工具函数模块
包含所有视图共用的基础函数
"""
import os
import re
import sys
import logging
from datetime import datetime
from django.http import FileResponse, Http404
from django.conf import settings
from ..models import OrgDetail
from ..config import get_config, _get_runtime_base_dir as get_runtime_base_dir

logger = logging.getLogger('work_tools.view')


def save_sql_file(sql_content, prefix='sql', dynamic_id=None):
    r"""
    保存SQL内容到配置的目录
    返回文件路径
    
    支持两种模式：
    - hierarchical: 按日期分层 {BASE_PATH}/{YYYYMM}/{DD}/{filename}.sql
    - flat: 单一文件夹 {BASE_PATH}/{filename}.sql
    """
    try:
        # 读取配置
        cfg = get_config()
        base_path = cfg.get('SQL_OUTPUT_BASE_PATH', r'D:\临时文件')
        mode = cfg.get('SQL_OUTPUT_MODE', 'hierarchical')
        date_format = cfg.get('SQL_OUTPUT_DATE_FORMAT', '%Y%m/%d')
        
        # 处理相对路径：如果是相对路径，基于运行时目录
        if not os.path.isabs(base_path):
            runtime_base = get_runtime_base_dir()
            base_path = os.path.join(runtime_base, base_path.lstrip('./'))
        
        now = datetime.now()
        
        # 根据模式生成目标路径
        if mode == 'flat':
            # 单一文件夹模式
            target_dir = base_path
        else:
            # 按日期分层模式（默认）
            date_subdir = now.strftime(date_format)
            # 规范化路径分隔符，将 / 替换为系统分隔符
            date_subdir = date_subdir.replace('/', os.sep).replace('\\', os.sep)
            target_dir = os.path.join(base_path, date_subdir)
        
        # 规范化整个路径
        target_dir = os.path.normpath(target_dir)
        
        # 创建目录
        os.makedirs(target_dir, exist_ok=True)
        
        # 生成文件名
        if dynamic_id:
            filename = f'{dynamic_id}_{prefix}.sql'
        else:
            timestamp = now.strftime('%H%M%S')
            filename = f'{prefix}_{timestamp}.sql'
        
        # 完整文件路径
        filepath = os.path.join(target_dir, filename)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        logger.info(f"[文件保存] SQL文件已保存: {filepath}")
        return filepath
        
    except Exception as e:
        # 失败时回退到运行时基础目录下的temp_files
        logger.error(f"[文件保存] 使用配置路径失败，回退到默认路径: {str(e)}")
        try:
            runtime_base = get_runtime_base_dir()
            now = datetime.now()
            year_month = now.strftime('%Y%m')
            day = now.strftime('%d')
            target_dir = os.path.join(runtime_base, 'temp_files', 'sql_output', year_month, day)
            os.makedirs(target_dir, exist_ok=True)
            
            if dynamic_id:
                filename = f'{dynamic_id}_{prefix}.sql'
            else:
                timestamp = now.strftime('%H%M%S')
                filename = f'{prefix}_{timestamp}.sql'
            
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            
            logger.info(f"[文件保存] 使用回退路径保存成功: {filepath}")
            return filepath
        except Exception as fallback_error:
            logger.error(f"[文件保存] 回退路径也失败: {str(fallback_error)}")
            raise


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


def download_validation_failure_view(request):
    """
    下载校验失败文件
    
    安全性考虑：
    - 仅允许下载validation_failures目录下的文件
    - 验证文件名格式（必须以validation_failed_开头且为.xlsx后缀）
    - 下载后删除临时文件
    """
    filename = request.GET.get('file', '').strip()
    
    # 验证文件名格式（安全性检查）
    if not filename:
        raise Http404("文件不存在")
    
    # 防止路径遍历攻击
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"检测到非法文件名访问: {filename}")
        raise Http404("非法文件名")
    
    # 验证文件名前缀和后缀
    if not filename.startswith('validation_failed_') or not filename.endswith('.xlsx'):
        logger.warning(f"文件名格式不正确: {filename}")
        raise Http404("文件格式不正确")
    
    # 构建文件路径（支持打包后的相对路径）
    runtime_base = get_runtime_base_dir()
    temp_dir = os.path.join(runtime_base, 'temp_uploads', 'validation_failures')
    filepath = os.path.join(temp_dir, filename)
    
    # 检查文件是否存在
    if not os.path.exists(filepath):
        logger.warning(f"文件不存在: {filepath}")
        raise Http404("文件不存在或已过期")
    
    try:
        # 返回文件
        response = FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        # 下载后删除文件（可选，可以通过定时任务清理）
        # os.remove(filepath)
        # logger.info(f"文件下载完成并已删除: {filename}")
        
        logger.info(f"文件下载成功: {filename}")
        return response
        
    except Exception as e:
        logger.error(f"文件下载失败: {filename}, error={str(e)}")
        raise Http404("文件读取失败")


__all__ = [
    'parse_ops_remark',
    'extract_company_code',
    'extract_company_name',
    '_unique_code_by_name',
    'normalize_item_id',
    'save_sql_file',
    'download_validation_failure_view',
]
