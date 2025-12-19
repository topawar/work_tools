"""
中文本地化Django模板标签
提供日期时间、数字等的中文格式化功能
"""
from django import template
from django.utils.safestring import mark_safe
from work_tools.utils.localization import localizer

register = template.Library()

@register.filter
def chinese_datetime(value, format_type='full'):
    """
    将日期时间格式化为中文格式
    
    用法:
    {{ datetime_obj|chinese_datetime }}
    {{ datetime_obj|chinese_datetime:"date" }}
    {{ datetime_obj|chinese_datetime:"short" }}
    """
    if not value:
        return ''
    return localizer.format_datetime(value, format_type)

@register.filter
def chinese_date(value):
    """
    将日期格式化为中文日期格式
    
    用法:
    {{ date_obj|chinese_date }}
    """
    if not value:
        return ''
    return localizer.format_datetime(value, 'date')

@register.filter
def chinese_number(value, use_chinese=False):
    """
    将数字格式化为中文格式
    
    用法:
    {{ number|chinese_number }}
    {{ number|chinese_number:True }}  # 使用中文数字
    """
    if value is None:
        return ''
    return localizer.format_number(value, use_chinese)

@register.filter
def file_size(value):
    """
    将字节数格式化为中文文件大小
    
    用法:
    {{ bytes|file_size }}
    """
    if not value:
        return '0 字节'
    return localizer.format_file_size(value)

@register.filter
def duration(value):
    """
    将秒数格式化为中文时间长度
    
    用法:
    {{ seconds|duration }}
    """
    if not value:
        return '0秒'
    return localizer.format_duration(value)

@register.filter
def relative_time(value):
    """
    获取相对时间描述
    
    用法:
    {{ datetime_obj|relative_time }}
    """
    if not value:
        return ''
    return localizer.get_relative_time(value)

@register.simple_tag
def current_time(format_type='full'):
    """
    获取当前时间的中文格式
    
    用法:
    {% current_time %}
    {% current_time "date" %}
    """
    return localizer.format_datetime(None, format_type)

@register.inclusion_tag('tags/chinese_datetime_display.html')
def datetime_display(dt, show_relative=True, format_type='short'):
    """
    显示日期时间的完整组件
    
    用法:
    {% datetime_display datetime_obj %}
    {% datetime_display datetime_obj show_relative=False %}
    """
    return {
        'datetime': dt,
        'formatted': localizer.format_datetime(dt, format_type) if dt else '',
        'relative': localizer.get_relative_time(dt) if dt and show_relative else '',
        'show_relative': show_relative
    }

@register.simple_tag
def chinese_messages():
    """
    获取中文化的常用消息文本
    """
    return {
        'loading': '加载中...',
        'saving': '保存中...',
        'success': '操作成功',
        'error': '操作失败',
        'confirm': '确认操作',
        'cancel': '取消',
        'delete': '删除',
        'edit': '编辑',
        'add': '添加',
        'save': '保存',
        'submit': '提交',
        'reset': '重置',
        'search': '搜索',
        'filter': '筛选',
        'export': '导出',
        'import': '导入',
        'upload': '上传',
        'download': '下载',
        'refresh': '刷新',
        'back': '返回',
        'next': '下一步',
        'previous': '上一步',
        'close': '关闭',
        'open': '打开',
        'enable': '启用',
        'disable': '禁用',
        'active': '激活',
        'inactive': '未激活',
        'online': '在线',
        'offline': '离线',
        'yes': '是',
        'no': '否',
        'all': '全部',
        'none': '无',
        'select_all': '全选',
        'clear_all': '清空',
        'required': '必填',
        'optional': '可选',
        'invalid': '无效',
        'valid': '有效',
        'empty': '空',
        'full': '满',
        'new': '新建',
        'old': '旧的',
        'updated': '已更新',
        'created': '已创建',
        'deleted': '已删除',
        'modified': '已修改',
        'unchanged': '未更改'
    }