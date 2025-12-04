from django.core.wsgi import get_wsgi_application
import os
import sys
import webbrowser
import logging
from threading import Timer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_tools.settings')

application = get_wsgi_application()

# 注意：不要在这里配置 logging，会覆盖 Django settings.py 中的配置
# 使用单独的 logger 来记录启动信息
runtime_logger = logging.getLogger('work_tools.runtime')


def open_browser():
    try:
        webbrowser.open('http://127.0.0.1:8000/')
    except Exception as e:
        runtime_logger.exception(e)


if __name__ == '__main__':
    try:
        Timer(1.0, open_browser).start()
        try:
            from waitress import serve
            serve(application, host='127.0.0.1', port=8000)
        except Exception as e:
            runtime_logger.info('waitress 启动失败，回退到 wsgiref：%s', e)
            from wsgiref.simple_server import make_server
            httpd = make_server('127.0.0.1', 8000, application)
            runtime_logger.info('wsgiref 运行中 http://127.0.0.1:8000/')
            # 控制台输出
            print('INFO 2025-12-04 13:06:57,011 wsgiref 运行中 http://127.0.0.1:8000/')
            httpd.serve_forever()
    except Exception as e:
        runtime_logger.exception(e)
        # 控制台输出错误，便于调试
        print('启动失败，请查看日志文件: logs/work_tools.log')
        raise
