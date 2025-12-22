# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller配置文件 - Work Tools便携式应用程序
使用waitress作为生产服务器，优化静态文件处理
"""

import os
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path.cwd()

# 收集Django静态文件路径
def get_django_static_paths():
    """获取Django相关的静态文件路径"""
    paths = []
    try:
        import django
        django_path = Path(django.__file__).parent
        # Django contrib admin 静态文件
        admin_static = django_path / 'contrib' / 'admin' / 'static'
        if admin_static.exists():
            paths.append((str(admin_static), 'django/contrib/admin/static'))
    except ImportError:
        pass
    return paths

# 数据文件配置
datas = [
    # work_tools 应用（包含所有Python文件、模板、静态文件）
    ('work_tools', 'work_tools'),
    
    # 收集后的静态文件目录
    ('static', 'static'),
    
    # 模板目录（如果在根目录有）
    ('templates', 'templates') if (project_root / 'templates').exists() else None,
    
    # 配置文件目录
    ('config', 'config') if (project_root / 'config').exists() else None,
    
    # 数据库文件
    ('db.sqlite3', '.') if (project_root / 'db.sqlite3').exists() else None,
]

# 添加Django静态文件
datas.extend(get_django_static_paths())

# 过滤None值
datas = [d for d in datas if d is not None]

# 隐藏导入
hiddenimports = [
    # Django核心
    'django',
    'django.contrib.admin',
    'django.contrib.admin.apps',
    'django.contrib.auth',
    'django.contrib.auth.apps',
    'django.contrib.contenttypes',
    'django.contrib.contenttypes.apps',
    'django.contrib.sessions',
    'django.contrib.sessions.apps',
    'django.contrib.messages',
    'django.contrib.messages.apps',
    'django.contrib.staticfiles',
    'django.contrib.staticfiles.apps',
    'django.core.management',
    'django.core.management.commands.runserver',
    'django.core.wsgi',
    'django.db.backends.sqlite3',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    
    # work_tools应用
    'work_tools',
    'work_tools.apps',
    'work_tools.settings',
    'work_tools.urls',
    'work_tools.wsgi',
    'work_tools.models',
    'work_tools.views',
    'work_tools.forms',
    'work_tools.middleware',
    
    # 生产服务器
    'waitress',
    'waitress.server',
    'waitress.task',
    'waitress.channel',
    'waitress.adjustments',
    
    # 静态文件中间件
    'whitenoise',
    'whitenoise.middleware',
    'whitenoise.base',
    'whitenoise.storage',
    'whitenoise.compress',
    
    # 数据处理
    'openpyxl',
    'pypinyin',
    'lxml',
    'lxml.etree',
    
    # 标准库
    'sqlite3',
    'json',
    'logging',
    'logging.handlers',
    'pathlib',
    'threading',
    'socket',
    'webbrowser',
    'hashlib',
    'tempfile',
    'shutil',
    'datetime',
    'time',
    're',
    'traceback',
    'psutil',
    
    # GUI库
    'tkinter',
    'tkinter.filedialog',
    'tkinter.dialog',
]

# 排除不需要的模块
excludes = [
    'pytest',
    'hypothesis',
    'unittest',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'PIL',
    'IPython',
    'jupyter',
]

# 分析
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WorkTools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 显示控制台便于调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WorkTools'
)
