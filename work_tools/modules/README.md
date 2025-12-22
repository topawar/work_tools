# 模块化目录结构

## 概述

为了更好地组织代码，我们将应用按功能模块进行了重新组织。每个模块包含其相关的视图(views)、模板(templates)和静态资源。

## 目录结构

```
work_tools/
├── modules/                    # 模块目录
│   ├── system_config/         # 系统配置模块
│   │   ├── __init__.py
│   │   └── views.py           # 视图函数
│   └── ...                    # 其他模块
│
├── templates/
│   └── modules/               # 模块模板
│       └── system_config/     # 系统配置模块模板
│           ├── system_config.html
│           ├── database_config.html
│           ├── file_path_config.html
│           └── cleanup_config.html
│
└── static/
    └── css/
        └── system-pages.css   # 系统配置页面专用样式
```

## 系统配置模块

### 文件位置

- **视图**: `work_tools/modules/system_config/views.py`
- **模板**: `work_tools/templates/modules/system_config/`
- **样式**: `work_tools/static/css/system-pages.css`

### 包含的页面

1. **SQL合并策略配置** (`system_config.html`)
   - 配置各个模块的SQL合并开关
   - 统计启用/禁用的模块数量

2. **数据库配置管理** (`database_config.html`)
   - 管理数据库连接配置
   - 添加、编辑、删除数据库配置

3. **文件路径配置** (`file_path_config.html`)
   - 配置SQL文件输出路径
   - 设置路径组织模式和日期格式

4. **临时文件清理配置** (`cleanup_config.html`)
   - 配置自动清理策略
   - 手动触发清理任务

### 样式特点

- **完全独立**: `system-pages.css` 不依赖任何外部CSS文件
- **简洁统一**: 所有系统配置页面使用相同的样式系统
- **响应式设计**: 支持桌面和移动端显示

## 使用方法

### 导入视图

```python
from work_tools.modules.system_config import (
    system_config_view,
    file_path_config_view,
    cleanup_config_view,
    cleanup_now_view
)
```

### URL配置

```python
from work_tools.modules.system_config import views as system_config_views

urlpatterns = [
    path('system/config/', system_config_views.system_config_view),
    path('system/file-path/', system_config_views.file_path_config_view),
    path('system/cleanup/', system_config_views.cleanup_config_view),
    path('system/cleanup-now/', system_config_views.cleanup_now_view),
]
```

## 优势

1. **模块化**: 每个功能模块的代码集中在一起，易于维护
2. **独立性**: 模块之间相互独立，减少耦合
3. **可扩展**: 添加新模块时结构清晰，不会影响现有模块
4. **易于测试**: 模块化结构便于单元测试和集成测试
