#!/usr/bin/env python
"""
最终测试脚本 - 验证所有组件
"""

def test_imports():
    """测试所有核心组件导入"""
    try:
        from work_tools.path_manager import PathManager
        from work_tools.database_manager import DatabaseManager
        from work_tools.configuration_manager import ConfigurationManager
        from work_tools.static_assets_manager import StaticAssetsManager
        from work_tools.application_launcher import ApplicationLauncher
        from work_tools.performance_monitor import PerformanceMonitor
        print('✓ 所有核心组件导入成功')
        return True
    except Exception as e:
        print(f'✗ 组件导入失败: {e}')
        return False

def test_basic_functionality():
    """测试基本功能"""
    try:
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试路径管理器
            exe_path = os.path.join(temp_dir, 'test.exe')
            from work_tools.path_manager import PathManager
            pm = PathManager(exe_path)
            print('✓ 路径管理器创建成功')
            
            # 测试配置管理器
            config_path = os.path.join(temp_dir, 'config.json')
            from work_tools.configuration_manager import ConfigurationManager
            cm = ConfigurationManager(config_path)
            result = cm.update_config(app_name='Test App')
            if result:
                print('✓ 配置管理器功能正常')
            else:
                print('⚠ 配置管理器功能异常')
            
            # 测试性能监控器
            from work_tools.performance_monitor import PerformanceMonitor
            perf = PerformanceMonitor(temp_dir)
            print('✓ 性能监控器创建成功')
            
        return True
    except Exception as e:
        print(f'✗ 基本功能测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_build_readiness():
    """测试构建就绪性"""
    try:
        import os
        
        # 检查关键文件
        required_files = [
            'main.py',
            'work_tools.spec',
            'build_exe.py',
            'work_tools/settings.py',
            'requirements.txt'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f'✗ 缺少关键文件: {missing_files}')
            return False
        else:
            print('✓ 所有关键文件存在')
        
        # 检查目录结构
        required_dirs = [
            'work_tools',
            'tests',
            'static',
            'logs'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print(f'⚠ 缺少目录: {missing_dirs}')
        else:
            print('✓ 目录结构完整')
        
        return True
    except Exception as e:
        print(f'✗ 构建就绪性检查失败: {e}')
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("Work Tools 便携式EXE打包 - 最终测试")
    print("=" * 60)
    
    tests = [
        ("组件导入测试", test_imports),
        ("基本功能测试", test_basic_functionality),
        ("构建就绪性测试", test_build_readiness)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"   测试失败")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！项目已准备好进行打包。")
        print("\n下一步:")
        print("1. 运行 'python build_exe.py' 构建可执行文件")
        print("2. 测试生成的exe文件")
        print("3. 创建分发包")
    else:
        print("❌ 部分测试失败，请修复问题后重新测试。")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)