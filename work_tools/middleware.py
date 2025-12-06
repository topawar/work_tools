"""请求日志中间件 - 简化版本,直接记录所有请求信息"""
import logging
import json
import time
from django.utils.deprecation import MiddlewareMixin

# 使用简化的日志器名称
logger = logging.getLogger('app.request')


class RequestLoggingMiddleware(MiddlewareMixin):
    """记录所有请求的详细信息"""

    def process_request(self, request):
        """请求开始时记录"""
        request._start_time = time.time()

        # 强制立即刷新日志
        try:
            log_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                'ip': self.get_client_ip(request),
            }

            if request.method == 'POST':
                # 记录POST数据（排除敏感字段）
                post_data = {}
                for key, value in request.POST.items():
                    if key not in ['csrfmiddlewaretoken', 'password']:
                        post_data[key] = value
                if post_data:
                    log_data['post_data'] = post_data

                # 记录上传的文件信息
                if request.FILES:
                    files_info = {}
                    for key, file in request.FILES.items():
                        files_info[key] = {
                            'name': file.name,
                            'size': file.size,
                            'content_type': file.content_type
                        }
                    log_data['files'] = files_info

            elif request.method == 'GET':
                # 记录GET参数
                if request.GET:
                    log_data['get_params'] = dict(request.GET)

            # 输出到日志文件和控制台
            log_msg = f"REQUEST START: {json.dumps(log_data, ensure_ascii=False)}"
            logger.info(log_msg)

            # 强制刷新所有handler
            for handler in logger.handlers:
                handler.flush()

            # 控制台输出
            print("=" * 100)
            print(f"\n[请求开始] {request.method} {request.path}")
            print(f"时间: {log_data['timestamp']}")
            if 'post_data' in log_data:
                print(
                    f"POST数据: {json.dumps(log_data['post_data'], ensure_ascii=False, indent=2)}")
            if 'files' in log_data:
                print(
                    f"文件上传: {json.dumps(log_data['files'], ensure_ascii=False, indent=2)}")
            print("=" * 100 + "\n")

        except Exception as e:
            print(f"[中间件错误] 记录请求开始失败: {e}")
            logger.error(f"记录请求开始失败: {e}", exc_info=True)

    def process_response(self, request, response):
        """请求结束时记录"""
        try:
            if hasattr(request, '_start_time'):
                duration = time.time() - request._start_time

                log_data = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration': f'{duration:.3f}s'
                }

                log_msg = f"REQUEST END: {json.dumps(log_data, ensure_ascii=False)}"
                logger.info(log_msg)

                # 强制刷新所有handler
                for handler in logger.handlers:
                    handler.flush()

                # 控制台输出
                print(
                    f"[请求结束] {request.method} {request.path} - 状态码: {response.status_code} - 耗时: {duration:.3f}秒\n")

        except Exception as e:
            print(f"[中间件错误] 记录请求结束失败: {e}")
            logger.error(f"记录请求结束失败: {e}", exc_info=True)

        return response

    def process_exception(self, request, exception):
        """记录异常"""
        try:
            error_msg = f"REQUEST EXCEPTION: {request.path} - {str(exception)}"
            logger.error(error_msg, exc_info=True)

            # 强制刷新所有handler
            for handler in logger.handlers:
                handler.flush()

            print(f"[请求异常] {request.path} - {exception}")
        except Exception as e:
            print(f"[中间件错误] 记录异常失败: {e}")

    @staticmethod
    def get_client_ip(request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
