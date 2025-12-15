# 打包配置完善设计

## 设计目标

完善项目的 PyInstaller 打包配置，确保所有新增模块、数据库文件正确打包，并支持端口参数传递和打包后临时文件清理功能。

## 背景分析

当前项目已具备基础打包配置（work_tools_onedir.spec 和 work_tools_onefile.spec），但存在以下待完善点：

1. 打包后需支持通过命令行参数指定端口号
2. 数据库文件需随程序打包发布
3. 新增的视图模块需加入隐藏导入列表
4. 临时文件清理功能需适配打包后的相对路径

## 核心需求

### 1. 新增模块打包支持

需确保以下新增视图模块被正确打包：

- work_tools.views.configurable_config（可配置化配置管理）
- work_tools.views.configurable_data（可配置化数据管理）
- work_tools.views.contract_creator（合同创建人修改）
- work_tools.views.database_config（数据库配置管理）
- work_tools.views.order_executor（订单执行人修改）
- work_tools.views.plan_date（需求计划日期修改）
- work_tools.views.user_org_manage（用户组织关系导入）

### 2. 数据库文件打包

**文件路径**：db.sqlite3（位于项目根目录）

**打包策略**：

- 数据库文件必须预先创建并随程序打包
- 打包后位置：与 exe 文件同级目录
- 禁止运行时动态生成数据库文件

**技术要点**：

- 在 spec 文件的 datas 配置中添加数据库文件映射
- 目标路径设置为当前目录（.）以确保 Django 能正确访问

### 3. 端口参数支持

**需求描述**：
打包后的 exe 程序应支持通过命令行参数指定服务端口，保持与源码运行时相同的参数接口。

**参数接口**：

- 短参数：-p [端口号]
- 长参数：--port [端口号]
- 默认端口：8000
- 示例：work_tools.exe -p 5000

**实现基础**：
run_app.py 已实现 argparse 命令行参数解析，打包后自动继承此功能，无需额外配置。

### 4. 临时文件清理适配

**目标目录清理规则**：

| 目录路径                         | 文件模式                  | 说明                  |
| -------------------------------- | ------------------------- | --------------------- |
| temp_uploads/validation_failures | validation*failed*\*.xlsx | 校验失败的 Excel 文件 |
| temp_uploads                     | _.csv, tmp_.csv           | CSV 临时上传文件      |
| logs                             | _.log._                   | 历史日志备份文件      |

**路径解析策略**：

- 源码运行：使用 Django 的 BASE_DIR
- 打包运行：使用 sys.executable 所在目录
- 统一通过 get_runtime_base_dir()函数获取基础路径

**关键设计**：
cleanup_temp_files.py 已实现打包模式检测逻辑，通过 sys.frozen 判断运行环境并动态调整路径基准，确保打包后清理的是 exe 同级目录下的相对路径。

## 配置文件修改方案

### work_tools_onefile.spec 修改点

**隐藏导入列表补充**：
在 hiddenimports 数组中补充以下新增视图模块：

- work_tools.views.configurable_config
- work_tools.views.configurable_data
- work_tools.views.contract_creator
- work_tools.views.database_config
- work_tools.views.order_executor
- work_tools.views.plan_date
- work_tools.views.user_org_manage

**数据文件打包配置**：
在 datas 数组中添加：

- 数据库文件：('db.sqlite3', '.')
- 配置目录：('config', 'config')

### work_tools_onedir.spec 修改点

**当前状态**：
该文件已包含完整的新增模块和数据库文件配置，无需额外修改。

**已配置内容**：

- 所有新增视图模块已在 hiddenimports 中声明
- db.sqlite3 已映射至打包根目录
- config 目录已正确打包

## 打包执行流程

### 单文件模式打包

**命令**：

```
pyinstaller work_tools_onefile.spec
```

**输出结构**：

```
dist/
  └── work_tools.exe（独立可执行文件）
```

**特点**：

- 所有依赖打包为单个 exe
- 首次启动需解压临时文件，启动较慢
- 分发便捷，适合简单部署场景

### 目录模式打包

**命令**：

```
pyinstaller work_tools_onedir.spec
```

**输出结构**：

```
dist/
  └── work_tools/
      ├── work_tools.exe（主程序）
      ├── _internal/（依赖库目录）
      ├── db.sqlite3（数据库文件）
      ├── config/（配置目录）
      ├── logs/（运行时日志目录）
      └── temp_uploads/（临时文件目录）
```

**特点**：

- 依赖库独立存放于\_internal 目录
- 启动速度快
- 便于运行时文件管理
- 推荐用于生产环境

## 运行时行为

### 数据库访问机制

**路径定位**：
Django 配置中的 BASE_DIR 在打包后指向 sys.\_MEIPASS 临时目录，需通过 settings.py 中的 get_runtime_base()函数适配实际运行目录。

**连接配置**：

- 数据库引擎：django.db.backends.sqlite3
- 文件名：db.sqlite3
- 超时设置：30 秒
- 位置：运行时基础目录根路径

### 端口参数传递

**使用示例**：

```
# 使用默认端口8000
work_tools.exe

# 指定端口5000
work_tools.exe -p 5000

# 使用长参数形式
work_tools.exe --port 5000

# 禁止自动打开浏览器
work_tools.exe --no-browser
```

**参数处理流程**：

1. exe 启动时加载 run_app.py
2. argparse 解析命令行参数
3. 提取 port 参数值
4. 传递给 waitress 或 wsgiref 服务器
5. 服务在指定端口启动

### 临时文件清理执行

**手动触发方式**：

```
# 在源码环境
python manage.py cleanup_temp_files

# 在打包环境（目录模式）
cd dist/work_tools
work_tools.exe manage.py cleanup_temp_files

# 在打包环境（单文件模式）
work_tools.exe manage.py cleanup_temp_files
```

**参数选项**：

- --hours [小时数]：指定过期时长，默认读取配置文件
- --dry-run：模拟运行，不实际删除文件
- --verbose：显示详细清理过程

**清理范围**：
无论源码或打包模式，均清理运行时基础目录下的相对路径，确保打包后清理的是 exe 同级目录内的临时文件。

## 配置管理要求

### app_config.json 配置项

临时文件清理功能依赖以下配置参数：

| 配置键                    | 数据类型 | 默认值 | 说明                 |
| ------------------------- | -------- | ------ | -------------------- |
| TEMP_FILE_CLEANUP_ENABLED | 布尔值   | true   | 是否启用清理功能     |
| TEMP_FILE_RETENTION_HOURS | 整数     | 24     | 文件保留时长（小时） |

**配置文件打包**：
config 目录已在 spec 文件中配置打包，确保打包后程序能读取配置参数。

## 依赖库确认

确保以下依赖库已安装并可被 PyInstaller 识别：

| 库名称   | 用途        | 收集方式      |
| -------- | ----------- | ------------- |
| django   | Web 框架    | collect_all   |
| openpyxl | Excel 处理  | collect_all   |
| waitress | WSGI 服务器 | hiddenimports |
| pypinyin | 拼音转换    | hiddenimports |
| argparse | 命令行参数  | hiddenimports |

## 验证检查点

### 打包后功能验证

**必须验证的功能点**：

1. **端口参数测试**

   - 默认端口启动：work_tools.exe
   - 自定义端口启动：work_tools.exe -p 5000
   - 确认服务在指定端口正常监听

2. **数据库访问测试**

   - 访问任意数据维护页面
   - 执行导入操作
   - 确认 SQLite 数据库读写正常

3. **新增模块访问测试**

   - 访问可配置化配置页面
   - 访问合同创建人修改页面
   - 访问订单执行人修改页面
   - 访问需求计划日期修改页面
   - 确认所有新增功能正常加载

4. **临时文件清理测试**

   - 手动创建过期测试文件
   - 执行清理命令：work_tools.exe manage.py cleanup_temp_files --verbose
   - 确认正确清理 exe 同级目录下的文件

5. **配置文件读取测试**
   - 修改 config/app_config.json 中的参数
   - 重启程序验证配置生效

### 常见问题排查

**问题 1：ModuleNotFoundError**

- 原因：新增模块未加入 hiddenimports
- 解决：在 spec 文件 hiddenimports 中补充缺失模块

**问题 2：数据库文件不存在**

- 原因：打包前 db.sqlite3 未创建或未正确配置打包路径
- 解决：确保数据库文件存在且在 spec 的 datas 中正确映射

**问题 3：端口参数不生效**

- 原因：打包时未正确处理 sys.argv
- 解决：检查 run_app.py 的 argparse 配置是否被打包

**问题 4：临时文件清理路径错误**

- 原因：未正确判断运行环境
- 解决：确认 cleanup_temp_files.py 中的 get_runtime_base_dir()逻辑正确

## 部署注意事项

### 首次部署准备

1. **数据库初始化**

   - 确保 db.sqlite3 已包含必要的表结构和基础数据
   - 执行所有 migrations 生成完整 schema
   - 初始化下拉框配置数据

2. **配置文件准备**

   - 检查 config/app_config.json 是否包含所需配置项
   - 根据部署环境调整配置参数

3. **目录权限确认**
   - 确保程序对 logs 目录有写权限
   - 确保程序对 temp_uploads 目录有读写权限
   - 确保程序对 sql_output 目录有写权限

### 更新部署流程

**场景 1：仅更新 exe 程序**

- 替换 work_tools.exe 文件
- 保留现有 db.sqlite3 和 config 目录
- 重启服务

**场景 2：更新数据库 schema**

- 备份现有 db.sqlite3
- 替换为新版数据库文件
- 必要时迁移旧数据

**场景 3：更新配置参数**

- 编辑 config/app_config.json
- 无需重新打包，重启服务即可生效

## 打包优化建议

### 体积优化

**排除无用库**：
在 excludes 中已排除以下不需要的库：

- tkinter 相关（GUI 库）
- pytest、unittest（测试框架）
- matplotlib、numpy、pandas（数据分析库）

**UPX 压缩**：
spec 文件中已启用 upx 压缩，可显著减小 exe 体积。

### 启动性能优化

**目录模式优先**：
生产环境推荐使用 onedir 模式，避免单文件模式的解压延迟。

**依赖精简**：
定期检查 hiddenimports 列表，移除不再使用的模块依赖。
