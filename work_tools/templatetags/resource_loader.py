"""
Django模板标签 - 资源加载
提供load_css和load_js标签，支持本地优先、CDN备选的加载策略
"""
from django import template
from django.utils.safestring import mark_safe
from work_tools.utils.resource_loader import resource_loader

register = template.Library()

@register.simple_tag
def load_css(local_path, cdn_url=None, inline_css=None):
    """
    加载CSS资源模板标签
    
    用法:
    {% load_css 'vendor/css/bootstrap.min.css' 'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css' %}
    {% load_css 'css/custom.css' %}
    """
    result = resource_loader.load_stylesheet(local_path, cdn_url, inline_css)
    return mark_safe(result)

@register.simple_tag
def load_js(local_path, cdn_url=None):
    """
    加载JavaScript资源模板标签
    
    用法:
    {% load_js 'vendor/js/bootstrap.bundle.min.js' 'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js' %}
    {% load_js 'js/custom.js' %}
    """
    result = resource_loader.load_script(local_path, cdn_url)
    return mark_safe(result)

@register.simple_tag
def load_bootstrap_css():
    """加载Bootstrap CSS的便捷标签"""
    cdn_url = resource_loader.get_cdn_url('bootstrap', 'css')
    return load_css('vendor/css/bootstrap.min.css', cdn_url)

@register.simple_tag
def load_bootstrap_js():
    """加载Bootstrap JS的便捷标签"""
    cdn_url = resource_loader.get_cdn_url('bootstrap', 'js')
    return load_js('vendor/js/bootstrap.bundle.min.js', cdn_url)

@register.simple_tag
def load_bootstrap_icons():
    """加载Bootstrap Icons的便捷标签"""
    cdn_url = resource_loader.get_cdn_url('bootstrap-icons', 'css')
    return load_css('vendor/css/bootstrap-icons.min.css', cdn_url)

@register.simple_tag
def load_jquery():
    """加载jQuery的便捷标签"""
    cdn_url = resource_loader.get_cdn_url('jquery', 'js')
    return load_js('vendor/js/jquery-3.6.0.min.js', cdn_url)

@register.simple_tag
def versioned_static(path):
    """
    为静态资源添加版本号
    
    用法:
    {% versioned_static 'css/style.css' %}
    """
    from work_tools.utils.performance import PerformanceOptimizer
    from django.contrib.staticfiles.storage import staticfiles_storage
    
    try:
        # 获取静态文件的完整路径
        if hasattr(staticfiles_storage, 'path'):
            file_path = staticfiles_storage.path(path)
            version = PerformanceOptimizer.get_file_hash(file_path)
        else:
            # 开发环境下使用时间戳
            import time
            version = str(int(time.time()))[:8]
        
        static_url = staticfiles_storage.url(path)
        separator = '&' if '?' in static_url else '?'
        return f"{static_url}{separator}v={version}"
        
    except Exception:
        # 降级到普通静态URL
        return staticfiles_storage.url(path)

@register.simple_tag
def preload_resource(path, resource_type='script'):
    """
    生成资源预加载标签
    
    用法:
    {% preload_resource 'js/app.js' 'script' %}
    {% preload_resource 'css/style.css' 'style' %}
    """
    versioned_url = versioned_static(path)
    
    if resource_type == 'script':
        return mark_safe(f'<link rel="preload" href="{versioned_url}" as="script">')
    elif resource_type == 'style':
        return mark_safe(f'<link rel="preload" href="{versioned_url}" as="style">')
    elif resource_type == 'font':
        return mark_safe(f'<link rel="preload" href="{versioned_url}" as="font" crossorigin>')
    else:
        return mark_safe(f'<link rel="preload" href="{versioned_url}">')

@register.simple_tag
def critical_css():
    """
    内联关键CSS样式
    """
    critical_styles = """
    <style>
    /* 关键渲染路径CSS */
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;background:#f9fafb}
    .loading-indicator{position:fixed;top:0;left:0;width:100%;height:4px;background:linear-gradient(90deg,#667eea 0%,#764ba2 100%);z-index:9999}
    .container{max-width:1200px;margin:0 auto;padding:0 1rem}
    .btn{display:inline-flex;align-items:center;gap:0.5rem;padding:0.75rem 1.5rem;border:none;border-radius:8px;cursor:pointer;transition:all 0.2s ease}
    .btn-primary{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white}
    </style>
    """
    return mark_safe(critical_styles)