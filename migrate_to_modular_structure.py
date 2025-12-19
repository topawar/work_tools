#!/usr/bin/env python3
"""
将系统配置相关文件迁移到模块化结构
"""
import os
import shutil

def migrate_files():
    """执行文件迁移"""
    
    print("🚀 开始迁移到模块化结构...\n")
    
    # 1. 移动模板文件
    template_migrations = [
        ('work_tools/templates/system_config.html', 'work_tools/templates/modules/system_config/system_config.html'),
        ('work_tools/templates/database_config.html', 'work_tools/templates/modules/system_config/database_config.html'),
        ('work_tools/templates/file_path_config.html', 'work_tools/templates/modules/system_config/file_path_config.html'),
        ('work_tools/templates/cleanup_config.html', 'work_tools/templates/modules/system_config/cleanup_config.html'),
    ]
    
    print("📁 迁移模板文件...")
    for src, dst in template_migrations:
        if os.path.exists(src):
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # 如果目标文件已存在，先备份
            if os.path.exists(dst):
                backup = dst + '.backup'
                if os.path.exists(backup):
                    os.remove(backup)
                shutil.copy2(dst, backup)
                print(f"   ⚠️  {os.path.basename(dst)} 已存在，已备份")
            
            # 复制文件（保留原文件作为备份）
            shutil.copy2(src, dst)
            print(f"   ✅ {os.path.basename(src)} -> modules/system_config/")
        else:
            print(f"   ⚠️  {src} 不存在，跳过")
    
    # 2. 备份旧的视图文件
    print("\n📦 备份旧视图文件...")
    old_view = 'work_tools/views/system_config.py'
    if os.path.exists(old_view):
        backup = old_view + '.old'
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(old_view, backup)
        print(f"   ✅ system_config.py -> system_config.py.old")
    
    # 3. 显示新结构
    print("\n📊 新的目录结构:")
    print("""
    work_tools/
    ├── modules/
    │   └── system_config/
    │       ├── __init__.py
    │       └── views.py              # 新的视图文件
    │
    ├── templates/
    │   └── modules/
    │       └── system_config/
    │           ├── system_config.html
    │           ├── database_config.html
    │           ├── file_path_config.html
    │           └── cleanup_config.html
    │
    ├── static/
    │   └── css/
    │       └── system-pages.css      # 独立的CSS文件
    │
    └── views/
        └── system_config.py.old      # 旧文件备份
    """)
    
    print("\n✨ 迁移完成！")
    print("\n⚠️  注意事项:")
    print("   1. 旧的模板文件仍保留在 work_tools/templates/ 下")
    print("   2. 旧的视图文件已备份为 system_config.py.old")
    print("   3. 需要更新 urls.py 以使用新的视图路径")
    print("   4. 确认功能正常后可删除旧文件")
    
    print("\n📝 下一步:")
    print("   1. 更新 work_tools/urls.py 中的导入:")
    print("      from work_tools.modules.system_config import views as system_config_views")
    print("   2. 测试所有系统配置页面")
    print("   3. 确认无误后删除旧文件")

if __name__ == '__main__':
    try:
        migrate_files()
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
