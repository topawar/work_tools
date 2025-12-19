# Work Tools 部署和分发指南

## 📋 概述

本指南详细说明如何构建、打包和分发 Work Tools 便携式应用程序。适用于开发人员和系统管理员。

## 🛠️ 开发环境准备

### 系统要求

- **操作系统**: Windows 10/11 (推荐用于构建Windows应用)
- **Python**: 3.8+ (推荐 3.11)
- **内存**: 至少 4GB
- **磁盘空间**: 至少 2GB 可用空间

### 安装依赖

1. **克隆项目**
   ```cmd
   git clone <repository-url>
   cd work_tools
   ```

2. **创建虚拟环境**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **安装Python依赖**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. **验证环境**
   ```cmd
   python manage.py check
   python -m pytest tests/ -v
   ```

## 🔨 构建流程

### 自动构建

使用提供的构建脚本：

```cmd
python build_exe.py
```

构建脚本会自动：
- 收集静态文件
- 验证依赖完整性
- 创建PyInstaller配置
- 生成可执行文件
- 验证构建结果

### 手动构建步骤

如果需要手动控制构建过程：

1. **收集静态文件**
   ```cmd
   python manage.py collectstatic --noinput
   ```

2. **运行PyInstaller**
   ```cmd
   pyinstaller work_tools.spec
   ```

3. **验证构建**
   ```cmd
   cd dist\work_tools
   work_tools.exe --version
   ```

### 构建配置

#### PyInstaller配置文件 (work_tools.spec)

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('work_tools/templates', 'work_tools/templates'),
        ('db.sqlite3', '.'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'work_tools.apps',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 应用程序图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='work_tools'
)
```

## 📦 打包和分发

### 创建分发包

1. **准备分发目录**
   ```cmd
   mkdir release
   cd release
   ```

2. **复制构建结果**
   ```cmd
   xcopy /E /I ..\dist\work_tools work_tools_portable
   ```

3. **添加文档文件**
   ```cmd
   copy ..\USER_GUIDE.md work_tools_portable\
   copy ..\README.md work_tools_portable\
   copy ..\LICENSE work_tools_portable\
   ```

4. **创建压缩包**
   ```cmd
   powershell Compress-Archive -Path work_tools_portable -DestinationPath work_tools_portable_v1.0.0.zip
   ```

### 分发包结构

```
work_tools_portable_v1.0.0.zip
└── work_tools_portable/
    ├── work_tools.exe          # 主程序
    ├── _internal/              # PyInstaller内部文件
    ├── static/                 # 静态文件
    ├── templates/              # 模板文件
    ├── db.sqlite3             # 数据库文件
    ├── app_config.json        # 配置文件
    ├── USER_GUIDE.md          # 用户指南
    ├── README.md              # 项目说明
    └── LICENSE                # 许可证
```

### 版本管理

#### 版本号规范

使用语义化版本控制 (SemVer)：
- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

示例：`1.2.3`

#### 发布清单

每次发布前检查：

- [ ] 所有测试通过
- [ ] 版本号已更新
- [ ] 更新日志已编写
- [ ] 文档已更新
- [ ] 构建成功
- [ ] 在干净环境中测试
- [ ] 性能测试通过
- [ ] 安全扫描通过

## 🧪 测试和验证

### 构建验证

1. **功能测试**
   ```cmd
   # 在构建目录中
   cd dist\work_tools
   work_tools.exe
   # 验证Web界面可以访问
   # 测试主要功能
   ```

2. **兼容性测试**
   - Windows 10 (多个版本)
   - Windows 11
   - Windows Server 2019/2022
   - 不同硬件配置

3. **性能测试**
   - 启动时间 < 15秒
   - 内存使用 < 200MB
   - 响应时间 < 2秒

### 自动化测试

```cmd
# 运行所有测试
python -m pytest tests/ -v

# 运行属性测试
python -m pytest tests/test_*_property_*.py -v

# 运行集成测试
python -m pytest tests/test_integration.py -v
```

## 🚀 部署策略

### 企业部署

1. **批量部署**
   - 使用组策略分发
   - 网络共享部署
   - 自动化脚本部署

2. **配置管理**
   - 统一配置文件
   - 环境变量配置
   - 注册表配置

3. **监控和维护**
   - 集中日志收集
   - 性能监控
   - 自动更新机制

### 个人用户部署

1. **简单部署**
   - 下载压缩包
   - 解压到目标目录
   - 双击运行

2. **自定义配置**
   - 修改配置文件
   - 设置环境变量
   - 创建桌面快捷方式

## 🔧 故障排除

### 构建问题

#### 1. PyInstaller导入错误

**问题**: 缺少隐藏导入

**解决方案**:
```python
# 在work_tools.spec中添加
hiddenimports=[
    'missing.module.name',
    # 其他缺失的模块
]
```

#### 2. 静态文件缺失

**问题**: 静态文件没有包含在构建中

**解决方案**:
```python
# 在work_tools.spec中添加
datas=[
    ('path/to/static', 'static'),
    # 其他数据文件
]
```

#### 3. 数据库文件问题

**问题**: 数据库文件路径错误

**解决方案**:
- 确保数据库文件在正确位置
- 检查路径配置
- 验证文件权限

### 运行时问题

#### 1. 端口冲突

**问题**: 默认端口被占用

**解决方案**:
- 应用程序会自动寻找可用端口
- 可以通过配置文件指定端口
- 检查防火墙设置

#### 2. 权限问题

**问题**: 文件访问权限不足

**解决方案**:
- 以管理员身份运行
- 检查文件夹权限
- 移动到用户目录

#### 3. 依赖库问题

**问题**: 缺少系统库

**解决方案**:
- 安装Visual C++ Redistributable
- 更新Windows系统
- 检查系统完整性

## 📊 性能优化

### 构建优化

1. **减小文件大小**
   ```python
   # 在spec文件中启用UPX压缩
   upx=True
   
   # 排除不必要的模块
   excludes=['tkinter', 'matplotlib']
   ```

2. **启动时间优化**
   - 延迟导入非关键模块
   - 优化Django设置
   - 减少启动时的文件操作

3. **内存使用优化**
   - 使用生成器而不是列表
   - 及时释放大对象
   - 优化数据库查询

### 运行时优化

1. **数据库优化**
   - 添加适当的索引
   - 优化查询语句
   - 定期清理数据

2. **静态文件优化**
   - 压缩CSS和JavaScript
   - 优化图片大小
   - 使用CDN（如果适用）

## 🔒 安全考虑

### 构建安全

1. **代码签名**
   ```cmd
   # 使用代码签名证书
   signtool sign /f certificate.pfx /p password work_tools.exe
   ```

2. **病毒扫描**
   - 构建后进行病毒扫描
   - 使用多个扫描引擎
   - 提交到VirusTotal

3. **完整性验证**
   ```cmd
   # 生成文件哈希
   certutil -hashfile work_tools.exe SHA256
   ```

### 运行时安全

1. **网络安全**
   - 默认只监听本地地址
   - 使用HTTPS（如果需要）
   - 实施访问控制

2. **数据安全**
   - 加密敏感数据
   - 安全的临时文件处理
   - 定期备份

## 📋 发布检查清单

### 发布前检查

- [ ] 代码审查完成
- [ ] 所有测试通过
- [ ] 文档更新完成
- [ ] 版本号正确
- [ ] 构建成功
- [ ] 兼容性测试通过
- [ ] 性能测试通过
- [ ] 安全扫描通过
- [ ] 用户验收测试完成

### 发布后检查

- [ ] 下载链接正常
- [ ] 安装测试成功
- [ ] 用户反馈收集
- [ ] 监控系统正常
- [ ] 支持文档可访问
- [ ] 更新通知发送

## 📞 支持和维护

### 技术支持

1. **问题跟踪**
   - 使用Issue跟踪系统
   - 分类和优先级管理
   - 响应时间承诺

2. **用户支持**
   - 提供详细文档
   - 常见问题解答
   - 技术支持联系方式

### 维护计划

1. **定期更新**
   - 安全补丁
   - 功能改进
   - 性能优化

2. **监控和分析**
   - 使用情况统计
   - 错误报告分析
   - 性能指标监控

---

**版本**: 1.0.0  
**更新日期**: 2024-12-15  
**文档语言**: 中文