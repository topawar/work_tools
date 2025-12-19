"""
性能优化中间件
提供响应压缩、缓存控制等功能
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings
from work_tools.utils.performance import PerformanceOptimizer

logger = logging.getLogger(__name__)

class PerformanceMiddleware(MiddlewareMixin):
    """性能优化中间件"""
    
    def process_request(self, request):
        """记录请求开始时间"""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """处理响应，添加性能优化"""
        
        # 计算响应时间
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # 记录慢请求
            if duration > 2.0:  # 超过2秒的请求
                logger.warning(f"慢请求: {request.path} 耗时 {duration:.3f}s")
        
        # 添加缓存控制头
        self.add_cache_headers(request, response)
        
        # 压缩响应（如果支持）
        if self.should_compress(request, response):
            response = PerformanceOptimizer.compress_response(response)
        
        # 添加安全头
        self.add_security_headers(response)
        
        return response
    
    def add_cache_headers(self, request, response):
        """添加缓存控制头"""
        
        # 静态资源缓存
        if request.path.startswith('/static/'):
            # 静态资源缓存1年
            response['Cache-Control'] = 'public, max-age=31536000'
            response['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        
        # API响应缓存
        elif request.path.startswith('/api/'):
            # API响应缓存5分钟
            response['Cache-Control'] = 'public, max-age=300'
        
        # 配置页面缓存
        elif 'config' in request.path:
            # 配置页面不缓存
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
    
    def should_compress(self, request, response):
        """判断是否应该压缩响应"""
        
        # 检查客户端是否支持gzip
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding:
            return False
        
        # 检查响应是否已经压缩
        if response.get('Content-Encoding'):
            return False
        
        # 检查响应大小（小于1KB的不压缩）
        if len(response.content) < 1024:
            return False
        
        return True
    
    def add_security_headers(self, response):
        """添加安全相关的HTTP头"""
        
        # 防止XSS攻击
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # 引用策略
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'