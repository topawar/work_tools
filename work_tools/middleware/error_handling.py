"""
错误处理中间件
提供统一的错误处理和日志记录
"""
import logging
import json
import traceback
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(MiddlewareMixin):
    """错误处理中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_exception(self, request, exception):
        """处理视图中发生的异常"""
        
        # 记录异常信息
        error_info = {
            'url': request.get_full_path(),
            'method': request.method,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc()
        }
        
        # 根据异常类型记录不同级别的日志
        if isinstance(exception, Http404):
            logger.warning(f"404错误: {error_info['url']}", extra=error_info)
        elif isinstance(exception, PermissionDenied):
            logger.warning(f"权限拒绝: {error_info['url']}", extra=error_info)
        elif isinstance(exception, SuspiciousOperation):
            logger.error(f"可疑操作: {error_info['url']}", extra=error_info)
        else:
            logger.error(f"服务器错误: {error_info['url']}", extra=error_info)
        
        # 根据请求类型返回不同的错误响应
        if request.content_type == 'application/json' or request.META.get('HTTP_ACCEPT', '').startswith('application/json'):
            return self.handle_ajax_error(request, exception, error_info)
        else:
            return self.handle_html_error(request, exception, error_info)
    
    def handle_ajax_error(self, request, exception, error_info):
        """处理AJAX请求的错误"""
        
        if isinstance(exception, Http404):
            return JsonResponse({
                'success': False,
                'error': '请求的资源不存在',
                'error_code': 'NOT_FOUND'
            }, status=404)
        
        elif isinstance(exception, PermissionDenied):
            return JsonResponse({
                'success': False,
                'error': '没有权限执行此操作',
                'error_code': 'PERMISSION_DENIED'
            }, status=403)
        
        elif isinstance(exception, SuspiciousOperation):
            return JsonResponse({
                'success': False,
                'error': '请求包含可疑内容',
                'error_code': 'SUSPICIOUS_OPERATION'
            }, status=400)
        
        else:
            # 服务器内部错误
            error_message = '服务器内部错误，请稍后重试'
            
            # 开发环境下显示详细错误信息
            if settings.DEBUG:
                error_message = str(exception)
            
            return JsonResponse({
                'success': False,
                'error': error_message,
                'error_code': 'INTERNAL_ERROR'
            }, status=500)
    
    def handle_html_error(self, request, exception, error_info):
        """处理HTML请求的错误"""
        
        context = {
            'error_info': error_info,
            'debug': settings.DEBUG
        }
        
        if isinstance(exception, Http404):
            return render(request, 'errors/404.html', context, status=404)
        
        elif isinstance(exception, PermissionDenied):
            return render(request, 'errors/403.html', context, status=403)
        
        elif isinstance(exception, SuspiciousOperation):
            return render(request, 'errors/400.html', context, status=400)
        
        else:
            # 服务器内部错误
            return render(request, 'errors/500.html', context, status=500)
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ResourceLoadingMiddleware(MiddlewareMixin):
    """资源加载监控中间件"""
    
    def process_request(self, request):
        """记录资源请求"""
        
        # 只记录静态资源请求
        if request.path.startswith('/static/'):
            logger.info(f"静态资源请求: {request.path}", extra={
                'url': request.path,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', '')
            })
        
        return None
    
    def process_response(self, request, response):
        """记录资源响应"""
        
        # 记录静态资源加载失败
        if request.path.startswith('/static/') and response.status_code >= 400:
            logger.warning(f"静态资源加载失败: {request.path} (状态码: {response.status_code})", extra={
                'url': request.path,
                'status_code': response.status_code,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', '')
            })
        
        return response