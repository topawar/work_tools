"""
资源加载器 - 支持本地优先、CDN备选的加载策略
"""
import os
import logging
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

class ResourceLoader:
    """资源加载器类，实现本地优先、CDN备选的加载策略"""
    
    # 中国可访问的CDN配置
    CDN_PROVIDERS = {
        'bootstrap': {
            'css': 'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css',
            'js': 'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js'
        },
        'bootstrap-icons': {
            'css': 'https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.10.0/font/bootstrap-icons.min.css'
        },
        'jquery': {
            'js': 'https://cdn.bootcdn.net/ajax/libs/jquery/3.6.0/jquery.min.js'
        }
    }
    
    # 内联降级样式
    FALLBACK_CSS = """
    <style>
    /* 基础降级样式 */
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }
    .container, .container-fluid { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
    .btn { display: inline-block; padding: 8px 16px; margin: 4px; border: 1px solid #ccc; background: #f8f9fa; text-decoration: none; border-radius: 4px; cursor: pointer; }
    .btn-primary { background: #007bff; color: white; border-color: #007bff; }
    .btn-success { background: #28a745; color: white; border-color: #28a745; }
    .btn-danger { background: #dc3545; color: white; border-color: #dc3545; }
    .form-control { width: 100%; padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; box-sizing: border-box; }
    .table { width: 100%; border-collapse: collapse; }
    .table th, .table td { padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left; }
    .table th { background: #f8f9fa; font-weight: 600; }
    .alert { padding: 12px 16px; margin: 16px 0; border: 1px solid transparent; border-radius: 4px; }
    .alert-success { color: #155724; background: #d4edda; border-color: #c3e6cb; }
    .alert-danger { color: #721c24; background: #f8d7da; border-color: #f5c6cb; }
    .alert-warning { color: #856404; background: #fff3cd; border-color: #ffeaa7; }
    .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
    .modal-dialog { position: relative; margin: 50px auto; max-width: 500px; background: white; border-radius: 4px; }
    .modal-header, .modal-body, .modal-footer { padding: 16px; }
    .modal-header { border-bottom: 1px solid #dee2e6; }
    .modal-footer { border-top: 1px solid #dee2e6; text-align: right; }
    </style>
    """
    
    def __init__(self):
        self.debug = getattr(settings, 'DEBUG', False)
    
    def check_resource_availability(self, path: str) -> bool:
        """检查本地资源是否可用"""
        try:
            if hasattr(staticfiles_storage, 'exists'):
                return staticfiles_storage.exists(path)
            else:
                # 开发环境下检查文件是否存在
                full_path = os.path.join(settings.BASE_DIR, 'work_tools', 'static', path)
                return os.path.exists(full_path)
        except Exception as e:
            logger.warning(f"检查资源可用性失败: {path}, 错误: {e}")
            return False
    
    def log_resource_status(self, resource: str, status: str, source: str = None) -> None:
        """记录资源加载状态"""
        message = f"资源加载 - {resource}: {status}"
        if source:
            message += f" (来源: {source})"
        
        if status in ['成功', 'success']:
            logger.info(message)
        elif status in ['降级', 'fallback']:
            logger.warning(message)
        else:
            logger.error(message)
    
    def load_stylesheet(self, local_path: str, cdn_url: str = None, fallback_inline: str = None) -> str:
        """
        加载CSS样式表
        优先级: 本地资源 -> CDN资源 -> 内联样式
        """
        try:
            # 1. 尝试加载本地资源
            if self.check_resource_availability(local_path):
                try:
                    static_url = staticfiles_storage.url(local_path)
                    self.log_resource_status(local_path, '成功', '本地')
                    return f'<link rel="stylesheet" href="{static_url}" onerror="window.resourceLoadError && window.resourceLoadError(this)">'
                except Exception as e:
                    logger.warning(f"本地资源URL生成失败: {local_path}, 错误: {e}")
            
            # 2. 尝试CDN资源
            if cdn_url:
                self.log_resource_status(local_path, '降级到CDN', 'CDN')
                return f'<link rel="stylesheet" href="{cdn_url}" onerror="window.resourceLoadError && window.resourceLoadError(this)">'
            
            # 3. 使用内联样式降级
            inline_css = fallback_inline or self.FALLBACK_CSS
            self.log_resource_status(local_path, '降级到内联样式', '内联')
            return mark_safe(inline_css)
            
        except Exception as e:
            logger.error(f"样式表加载完全失败: {local_path}, 错误: {e}")
            # 返回最基本的内联样式
            return mark_safe(self.FALLBACK_CSS)
    
    def load_script(self, local_path: str, cdn_url: str = None) -> str:
        """
        加载JavaScript脚本
        优先级: 本地资源 -> CDN资源
        """
        try:
            # 1. 尝试加载本地资源
            if self.check_resource_availability(local_path):
                try:
                    static_url = staticfiles_storage.url(local_path)
                    self.log_resource_status(local_path, '成功', '本地')
                    return f'<script src="{static_url}" onerror="window.resourceLoadError && window.resourceLoadError(this)"></script>'
                except Exception as e:
                    logger.warning(f"本地资源URL生成失败: {local_path}, 错误: {e}")
            
            # 2. 尝试CDN资源
            if cdn_url:
                self.log_resource_status(local_path, '降级到CDN', 'CDN')
                return f'<script src="{cdn_url}" onerror="window.resourceLoadError && window.resourceLoadError(this)"></script>'
            
            # 3. JavaScript没有内联降级，记录错误
            self.log_resource_status(local_path, '加载失败', '无可用资源')
            return '<!-- JavaScript资源加载失败 -->'
            
        except Exception as e:
            logger.error(f"脚本加载完全失败: {local_path}, 错误: {e}")
            return '<!-- JavaScript资源加载失败 -->'
    
    def get_cdn_url(self, resource_type: str, file_type: str) -> str:
        """获取预配置的CDN URL"""
        return self.CDN_PROVIDERS.get(resource_type, {}).get(file_type)

# 全局资源加载器实例
resource_loader = ResourceLoader()