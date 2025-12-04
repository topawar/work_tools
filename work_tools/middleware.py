import logging
import json
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('work_tools.request')


class RequestLoggingMiddleware(MiddlewareMixin):
    """记录所有请求的详细信息"""

    def process_request(self, request):
        """请求开始时记录"""
        request._start_time = time.time()

        # 记录请求基本信息
        log_data = {
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'ip': self.get_client_ip(request),
        }

        if request.method == 'POST':
            # 记录POST数据（排除文件）
            post_data = {}
            for key, value in request.POST.items():
                if key not in ['csrfmiddlewaretoken']:
                    post_data[key] = value
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

        # 同时输出到日志文件和控制台
        log_message = f"REQUEST START: {json.dumps(log_data, ensure_ascii=False)}"
        logger.info(log_message)
        print("=" * 100)
        print(f"\n[请求开始] {request.method} {request.path}")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        if 'post_data' in log_data:
            print(
                f"POST数据: {json.dumps(log_data['post_data'], ensure_ascii=False, indent=2)}")
        if 'files' in log_data:
            print(
                f"文件上传: {json.dumps(log_data['files'], ensure_ascii=False, indent=2)}")
        print("=" * 100 + "\n")

    def process_response(self, request, response):
        """请求结束时记录"""
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time

            log_data = {
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': f'{duration:.3f}s'
            }

            # 同时输出到日志文件和控制台
            log_message = f"REQUEST END: {json.dumps(log_data, ensure_ascii=False)}"
            logger.info(log_message)
            print(
                f"[请求结束] {request.method} {request.path} - 状态码: {response.status_code} - 耗时: {duration:.3f}秒\n")

        return response

    def process_exception(self, request, exception):
        """记录异常"""
        logger.error(
            f"REQUEST EXCEPTION: {request.path} - {str(exception)}", exc_info=True)

    @staticmethod
    def get_client_ip(request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
