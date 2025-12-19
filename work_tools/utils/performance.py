"""
性能优化工具
提供静态资源压缩、缓存管理等功能
"""
import os
import hashlib
import gzip
import time
from django.conf import settings
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.http import HttpResponse

class PerformanceOptimizer:
    """性能优化工具类"""
    
    @staticmethod
    def get_file_hash(file_path):
        """获取文件的MD5哈希值，用于版本控制"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except (IOError, OSError):
            return str(int(time.time()))[:8]
    
    @staticmethod
    def should_compress(content_type):
        """判断是否应该压缩响应"""
        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/xml',
            'application/xml'
        ]
        return any(ct in content_type for ct in compressible_types)
    
    @staticmethod
    def compress_response(response):
        """压缩HTTP响应"""
        if not response.content:
            return response
            
        content_type = response.get('Content-Type', '')
        if not PerformanceOptimizer.should_compress(content_type):
            return response
        
        try:
            compressed_content = gzip.compress(response.content)
            if len(compressed_content) < len(response.content):
                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))
        except Exception:
            pass  # 压缩失败时保持原内容
            
        return response