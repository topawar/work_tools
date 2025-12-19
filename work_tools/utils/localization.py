"""
中文本地化工具
提供日期时间格式化、数字格式化等本地化功能
"""
import datetime
from django.utils import timezone
from django.conf import settings

class ChineseLocalizer:
    """中文本地化工具类"""
    
    # 中文数字映射
    CHINESE_NUMBERS = {
        0: '零', 1: '一', 2: '二', 3: '三', 4: '四',
        5: '五', 6: '六', 7: '七', 8: '八', 9: '九'
    }
    
    # 中文单位
    CHINESE_UNITS = ['', '十', '百', '千', '万', '十万', '百万', '千万', '亿']
    
    # 星期映射
    WEEKDAYS = {
        0: '星期一', 1: '星期二', 2: '星期三', 3: '星期四',
        4: '星期五', 5: '星期六', 6: '星期日'
    }
    
    # 月份映射
    MONTHS = {
        1: '一月', 2: '二月', 3: '三月', 4: '四月', 5: '五月', 6: '六月',
        7: '七月', 8: '八月', 9: '九月', 10: '十月', 11: '十一月', 12: '十二月'
    }
    
    @classmethod
    def format_datetime(cls, dt=None, format_type='full'):
        """
        格式化日期时间为中文格式
        
        Args:
            dt: datetime对象，默认为当前时间
            format_type: 格式类型 ('full', 'date', 'time', 'short')
        
        Returns:
            str: 格式化后的中文日期时间字符串
        """
        if dt is None:
            dt = timezone.now()
        
        # 确保使用中国时区
        if timezone.is_aware(dt):
            china_tz = timezone.get_fixed_timezone(480)  # UTC+8
            dt = dt.astimezone(china_tz)
        
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        second = dt.second
        weekday = dt.weekday()
        
        if format_type == 'full':
            return f"{year}年{month}月{day}日 {cls.WEEKDAYS[weekday]} {hour:02d}:{minute:02d}:{second:02d}"
        elif format_type == 'date':
            return f"{year}年{month}月{day}日"
        elif format_type == 'time':
            return f"{hour:02d}:{minute:02d}:{second:02d}"
        elif format_type == 'short':
            return f"{year}年{month}月{day}日 {hour:02d}:{minute:02d}"
        else:
            return str(dt)
    
    @classmethod
    def format_number(cls, number, use_chinese=False):
        """
        格式化数字为中文格式
        
        Args:
            number: 要格式化的数字
            use_chinese: 是否使用中文数字
        
        Returns:
            str: 格式化后的数字字符串
        """
        if not isinstance(number, (int, float)):
            return str(number)
        
        if use_chinese and isinstance(number, int) and 0 <= number <= 99:
            return cls._number_to_chinese(number)
        
        # 使用中文千分位分隔符
        if isinstance(number, float):
            return f"{number:,.2f}".replace(',', '，')
        else:
            return f"{number:,}".replace(',', '，')
    
    @classmethod
    def _number_to_chinese(cls, num):
        """将数字转换为中文数字"""
        if num == 0:
            return cls.CHINESE_NUMBERS[0]
        
        if num < 10:
            return cls.CHINESE_NUMBERS[num]
        
        if num < 20:
            if num == 10:
                return '十'
            else:
                return f"十{cls.CHINESE_NUMBERS[num % 10]}"
        
        if num < 100:
            tens = num // 10
            ones = num % 10
            if ones == 0:
                return f"{cls.CHINESE_NUMBERS[tens]}十"
            else:
                return f"{cls.CHINESE_NUMBERS[tens]}十{cls.CHINESE_NUMBERS[ones]}"
        
        return str(num)  # 超过99的数字直接返回阿拉伯数字
    
    @classmethod
    def format_file_size(cls, size_bytes):
        """
        格式化文件大小为中文单位
        
        Args:
            size_bytes: 文件大小（字节）
        
        Returns:
            str: 格式化后的文件大小字符串
        """
        if size_bytes == 0:
            return "0 字节"
        
        units = ['字节', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    @classmethod
    def format_duration(cls, seconds):
        """
        格式化时间长度为中文
        
        Args:
            seconds: 秒数
        
        Returns:
            str: 格式化后的时间长度字符串
        """
        if seconds < 60:
            return f"{int(seconds)}秒"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            if remaining_seconds == 0:
                return f"{int(minutes)}分钟"
            else:
                return f"{int(minutes)}分钟{int(remaining_seconds)}秒"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours < 24:
            if remaining_minutes == 0:
                return f"{int(hours)}小时"
            else:
                return f"{int(hours)}小时{int(remaining_minutes)}分钟"
        
        days = hours // 24
        remaining_hours = hours % 24
        
        if remaining_hours == 0:
            return f"{int(days)}天"
        else:
            return f"{int(days)}天{int(remaining_hours)}小时"
    
    @classmethod
    def get_relative_time(cls, dt):
        """
        获取相对时间描述
        
        Args:
            dt: datetime对象
        
        Returns:
            str: 相对时间描述
        """
        now = timezone.now()
        if timezone.is_aware(dt):
            china_tz = timezone.get_fixed_timezone(480)  # UTC+8
            dt = dt.astimezone(china_tz)
            now = now.astimezone(china_tz)
        
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return "昨天"
            elif diff.days < 7:
                return f"{diff.days}天前"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks}周前"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months}个月前"
            else:
                years = diff.days // 365
                return f"{years}年前"
        
        seconds = diff.seconds
        if seconds < 60:
            return "刚刚"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟前"
        else:
            hours = seconds // 3600
            return f"{hours}小时前"

# 全局本地化实例
localizer = ChineseLocalizer()