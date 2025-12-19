#!/usr/bin/env python
"""
打包前静态文件收集脚本
确保所有静态文件都被正确收集到static目录中
"""

import os
import sys
import shutil
import logging
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_tools.settings')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def collect_django_static_files(logger):
    """收集Django静态文件"""
    try:
        import django
        django.setup()
        
        from django.core.management import execute_from_command_line
        
        logger.info("开始收集Django静态文件...")
        
        # 保存原始argv
        original_argv = sys.argv
        
        try:
            # 执行collectstatic命令
            sys.argv = ['manage.py', 'collectstatic', '--noinput', '--clear', '--verbosity=2']
            execute_from_command_line(sys.argv)
            logger.info("Django静态文件收集完成")
            return True
        finally:
            sys.argv = original_argv
            
    except Exception as e:
        logger.error(f"Django静态文件收集失败: {e}")
        return False

def collect_admin_static_files(logger):
    """手动收集Django admin静态文件"""
    try:
        import django
        from django.contrib import admin
        
        # Django admin静态文件源目录
        admin_static_source = Path(admin.__file__).parent / 'static'
        admin_static_target = project_root / 'static' / 'admin'
        
        if admin_static_source.exists():
            logger.info(f"复制Django admin静态文件: {admin_static_source} -> {admin_static_target}")
            
            # 如果目标目录存在，先删除
            if admin_static_target.exists():
                shutil.rmtree(admin_static_target)
            
            # 复制admin静态文件
            shutil.copytree(admin_static_source / 'admin', admin_static_target)
            logger.info("Django admin静态文件复制完成")
            return True
        else:
            logger.warning("Django admin静态文件源目录不存在")
            return False
            
    except Exception as e:
        logger.error(f"复制Django admin静态文件失败: {e}")
        return False

def collect_app_static_files(logger):
    """收集应用静态文件"""
    try:
        app_static_source = project_root / 'work_tools' / 'static'
        app_static_target = project_root / 'static' / 'work_tools'
        
        if app_static_source.exists():
            logger.info(f"复制应用静态文件: {app_static_source} -> {app_static_target}")
            
            # 如果目标目录存在，先删除
            if app_static_target.exists():
                shutil.rmtree(app_static_target)
            
            # 复制应用静态文件
            shutil.copytree(app_static_source, app_static_target)
            logger.info("应用静态文件复制完成")
            return True
        else:
            logger.info("应用静态文件目录不存在，跳过")
            return True
            
    except Exception as e:
        logger.error(f"复制应用静态文件失败: {e}")
        return False

def verify_static_files(logger):
    """验证静态文件收集结果"""
    static_root = project_root / 'static'
    
    if not static_root.exists():
        logger.error("静态文件根目录不存在")
        return False
    
    # 检查关键文件
    critical_files = [
        'admin/css/base.css',
        'admin/css/login.css',
        'admin/js/core.js',
        'admin/js/admin/RelatedObjectLookups.js'
    ]
    
    missing_files = []
    for file_path in critical_files:
        full_path = static_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"关键静态文件缺失: {missing_files}")
        return False
    
    # 统计文件数量
    total_files = sum(1 for _ in static_root.rglob('*') if _.is_file())
    total_size = sum(f.stat().st_size for f in static_root.rglob('*') if f.is_file())
    
    logger.info(f"静态文件验证通过: {total_files} 个文件, 总大小: {total_size / 1024 / 1024:.2f} MB")
    return True

def main():
    """主函数"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("开始收集打包用静态文件")
    logger.info("=" * 60)
    
    success = True
    
    # 1. 收集Django静态文件
    if not collect_django_static_files(logger):
        success = False
    
    # 2. 手动收集admin静态文件（确保完整）
    if not collect_admin_static_files(logger):
        success = False
    
    # 3. 收集应用静态文件
    if not collect_app_static_files(logger):
        success = False
    
    # 4. 验证收集结果
    if not verify_static_files(logger):
        success = False
    
    logger.info("=" * 60)
    if success:
        logger.info("✓ 静态文件收集完成，可以开始打包")
    else:
        logger.error("✗ 静态文件收集失败，请检查错误信息")
    logger.info("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)