#!/usr/bin/env python3
"""
验证模块化结构是否正确配置
"""
import os
import sys

def verify_structure():
    """验证目录结构"""
    print("🔍 验证模块化结构...\n")
    
    checks = []
    
    # 1. 检查模块目录
    print("📁 检查模块目录...")
    module_files = [
        'work_tools/modules/__init__.py',
        'work_tools/modules/system_config/__init__.py',
        'work_tools/modules/system_config/views.py',
    ]
    
    for file in module_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
            checks.append(True)
        else:
            print(f"   ❌ {file} 不存在")
            checks.append(False)
    
    # 2. 检查模板目录
    print("\n📄 检查模板目录...")
    template_files = [
        'work_tools/templates/modules/system_config/system_config.html',
        'work_tools/templates/modules/system_config/database_config.html',
        'work_tools/templates/modules/system_config/file_path_config.html',
        'work_tools/templates/modules/system_config/cleanup_config.html',
    ]
    
    for file in template_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
            checks.append(True)
        else:
            print(f"   ❌ {file} 不存在")
            checks.append(False)
    
    # 3. 检查CSS文件
    print("\n🎨 检查CSS文件...")
    css_file = 'work_tools/static/css/system-pages.css'
    if os.path.exists(css_file):
        size = os.path.getsize(css_file)
        print(f"   ✅ {css_file} ({size} 字节)")
        checks.append(True)
    else:
        print(f"   ❌ {css_file} 不存在")
        checks.append(False)
    
    # 4. 检查views/__init__.py的导入
    print("\n🔗 检查导入配置...")
    views_init = 'work_tools/views/__init__.py'
    if os.path.exists(views_init):
        with open(views_init, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'work_tools.modules.system_config.views' in content:
            print(f"   ✅ views/__init__.py 已更新为使用新模块")
            checks.append(True)
        else:
            print(f"   ❌ views/__init__.py 未更新导入")
            checks.append(False)
    else:
        print(f"   ❌ {views_init} 不存在")
        checks.append(False)
    
    # 5. 检查备份文件
    print("\n📦 检查备份文件...")
    backup_file = 'work_tools/views/system_config.py.old'
    if os.path.exists(backup_file):
        print(f"   ✅ {backup_file} (旧文件已备份)")
        checks.append(True)
    else:
        print(f"   ⚠️  {backup_file} 不存在 (可能已删除)")
        checks.append(True)  # 不影响结果
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    print(f"验证结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！模块化结构配置正确。")
        print("\n✅ 可以启动Django服务器测试:")
        print("   python manage.py runserver")
        print("\n📝 测试页面:")
        print("   • http://localhost:8000/system/config/")
        print("   • http://localhost:8000/system/file-path/")
        print("   • http://localhost:8000/system/cleanup/")
        print("   • http://localhost:8000/database-config/")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请检查上述错误。")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(verify_structure())
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
