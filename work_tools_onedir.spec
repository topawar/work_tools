# -*- mode: python ; coding: utf-8 -*-
"""
Work Tools - 目录模式打包配置
使用PyInstaller将Django应用打包为目录结构(exe + _internal)
"""

from PyInstaller.utils.hooks import collect_all

# 收集Django和openpyxl的完整依赖
datas = []
binaries = []
hiddenimports = []

# 收集Django完整依赖
tmp_ret = collect_all('django')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 收集openpyxl完整依赖
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 添加应用模板和静态文件
datas += [
    ('work_tools/templates', 'work_tools/templates'),
    ('work_tools/static', 'work_tools/static'),
    ('work_tools/migrations', 'work_tools/migrations'),
]

# 添加work_tools所有视图模块的隐藏导入
hiddenimports += [
    # Django核心模块
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.core.management',
    'django.core.management.commands',
    'django.db.backends.sqlite3',
    # work_tools核心模块
    'work_tools',
    'work_tools.apps',
    'work_tools.middleware',
    'work_tools.config',
    'work_tools.logger_utils',
    'work_tools.sql_merge',
    'work_tools.dropdown_utils',
    'work_tools.validation_utils',
    'work_tools.navigation',
    'work_tools.forms',
    'work_tools.models',
    # work_tools视图模块
    'work_tools.views',
    'work_tools.views.appr_state',
    'work_tools.views.base',
    'work_tools.views.contract_budget',
    'work_tools.views.contract_item',
    'work_tools.views.contract_price',
    'work_tools.views.contract_terminate',
    'work_tools.views.contract_unit',
    'work_tools.views.dropdown_config',
    'work_tools.views.enddate',
    'work_tools.views.erp_terminate',
    'work_tools.views.gov_report',
    'work_tools.views.importance',
    'work_tools.views.item_manage',
    'work_tools.views.job_manage',
    'work_tools.views.org_api',
    'work_tools.views.price_type',
    'work_tools.views.project_round',
    'work_tools.views.sourcing_terminate',
    'work_tools.views.system_config',
    'work_tools.views.use_list',
    # 第三方依赖
    'waitress',
    'pypinyin',
]

# 排除不需要的模块
excludes = [
    'tkinter',
    'tk',
    'tcl',
    '_tkinter',
    'pytest',
    'unittest',
    'test',
    'matplotlib',
    'numpy',
    'pandas',
]

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
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
    name='work_tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='work_tools',
)
