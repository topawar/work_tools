"""
临时文件清理管理命令
用于定时清理过期的临时文件
支持打包后的相对路径
"""
import os
import sys
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from work_tools.config import get_config

logger = logging.getLogger('work_tools.view')


def get_runtime_base_dir():
    """
    获取运行时的基础目录
    支持打包后的exe和源码运行两种模式
    """
    # 检查是否为打包后的exe运行
    if getattr(sys, 'frozen', False):
        # 打包后，exe所在目录
        return os.path.dirname(sys.executable)
    else:
        # 源码运行，使用Django的BASE_DIR
        return settings.BASE_DIR


class Command(BaseCommand):
    help = '清理过期的临时文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=None,
            help='文件过期时长（小时），不指定则使用配置值'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不实际删除文件'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细日志'
        )

    def handle(self, *args, **options):
        """执行清理任务"""
        # 读取配置
        cfg = get_config()
        enabled = cfg.get('TEMP_FILE_CLEANUP_ENABLED', True)
        
        if not enabled:
            msg = '[清理任务] 清理功能未启用，跳过'
            logger.info(msg)
            self.stdout.write(self.style.WARNING(msg))
            return
        
        # 获取过期时长
        hours = options['hours'] or cfg.get('TEMP_FILE_RETENTION_HOURS', 24)
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        msg = f'[清理任务] 开始清理临时文件（过期时长: {hours}小时, 模拟运行: {dry_run}）'
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))
        
        # 清理临时目录
        total_cleaned = 0
        total_size = 0
        
        # 定义需要清理的目录和文件模式
        # 使用运行时基础目录，支持打包后的相对路径
        runtime_base = get_runtime_base_dir()
        cleanup_targets = [
            {
                'dir': os.path.join(runtime_base, 'temp_uploads', 'validation_failures'),
                'patterns': ['validation_failed_*.xlsx'],
                'description': '校验失败文件'
            },
            {
                'dir': os.path.join(runtime_base, 'temp_uploads'),
                'patterns': ['*.csv', 'tmp*.csv'],
                'description': 'CSV临时文件'
            },
            {
                'dir': os.path.join(runtime_base, 'logs'),
                'patterns': ['*.log.*'],  # 清理旧的日志备份文件
                'description': '日志备份文件'
            },
        ]
        
        if verbose:
            msg = f'[清理任务] 运行时基础目录: {runtime_base}'
            logger.info(msg)
            self.stdout.write(msg)
        
        for target in cleanup_targets:
            target_dir = target['dir']
            patterns = target['patterns']
            description = target['description']
            
            if not os.path.exists(target_dir):
                if verbose:
                    msg = f'[清理任务] 目录不存在，跳过: {target_dir}'
                    logger.warning(msg)
                    self.stdout.write(self.style.WARNING(msg))
                continue
            
            cleaned, size = self._cleanup_directory(
                target_dir, patterns, hours, dry_run, verbose
            )
            total_cleaned += cleaned
            total_size += size
            
            msg = f'[清理任务] {description}: 清理 {cleaned} 个文件, 释放 {size / 1024 / 1024:.2f} MB'
            logger.info(msg)
            self.stdout.write(self.style.SUCCESS(msg))
        
        # 输出统计信息
        msg = f'[清理任务] 完成！共清理 {total_cleaned} 个文件，释放 {total_size / 1024 / 1024:.2f} MB'
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))

    def _cleanup_directory(self, directory, patterns, hours, dry_run, verbose):
        """
        清理指定目录中的过期文件
        
        Args:
            directory: 目标目录
            patterns: 文件名模式列表
            hours: 过期时长（小时）
            dry_run: 是否模拟运行
            verbose: 是否显示详细信息
            
        Returns:
            (清理文件数, 释放空间字节数)
        """
        import fnmatch
        
        cleaned_count = 0
        total_size = 0
        now = datetime.now()
        
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                # 跳过目录
                if os.path.isdir(filepath):
                    continue
                
                # 检查文件名是否匹配模式
                matched = any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)
                if not matched:
                    continue
                
                # 检查文件是否过期
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    age_hours = (now - file_mtime).total_seconds() / 3600
                    
                    if age_hours <= hours:
                        continue
                    
                    # 文件已过期
                    file_size = os.path.getsize(filepath)
                    
                    if dry_run:
                        if verbose:
                            msg = f'[清理任务] [模拟] 将删除: {filename} (过期: {age_hours:.1f}小时)'
                            self.stdout.write(msg)
                    else:
                        os.remove(filepath)
                        if verbose:
                            msg = f'[清理任务] 已删除: {filename} (过期: {age_hours:.1f}小时)'
                            logger.info(msg)
                            self.stdout.write(msg)
                    
                    cleaned_count += 1
                    total_size += file_size
                    
                except Exception as e:
                    msg = f'[清理任务] 处理文件失败: {filename}, error={str(e)}'
                    logger.error(msg)
                    if verbose:
                        self.stdout.write(self.style.ERROR(msg))
                    continue
                    
        except Exception as e:
            msg = f'[清理任务] 扫描目录失败: {directory}, error={str(e)}'
            logger.error(msg)
            self.stdout.write(self.style.ERROR(msg))
        
        return cleaned_count, total_size

