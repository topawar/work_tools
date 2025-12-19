# URL配置更新指南

## 概述
系统配置模块已迁移到模块化结构，需要更新 `work_tools/urls.py` 中的导入路径。

## 当前目录结构

```
work_tools/
├── modules/
│   └── system_config/          ✅ 新位置
│       ├── __init__.py
│       └── views.py
│
├── templates/
│   └── modules/
│       └── system_config/      ✅ 新位置
│           ├── system_config.html
│           ├── database_config.html
│           ├── file_path_config.html
│           └── cleanup_config.html
│
└── views/
    └── system_config.py.old    📦 旧文件备份
```

## 需要更新的文件

### 1. work_tools/urls.py

#### 旧的导入方式（需要替换）
```python
from .views import system_config
```

#### 新的导入方式
```python
from work_tools.modules.system_config import views as system_config_views
```

#### URL模式更新

**旧的方式:**
```python
path('system/config/', system_config.system_config_view, name='system_config'),
path('system/file-path/', system_config.file_path_config_view, name='file_path_config'),
path('system/cleanup/', system_config.cleanup_config_view, name='cleanup_config'),
path('system/select-folder/', system_config.select_folder_api, name='select_folder_api'),
path('system/cleanup-now/', system_config.cleanup_now_view, name='cleanup_now'),
```

**新的方式:**
```python
path('system/config/', system_config_views.system_config_view, name='system_config'),
path('system/file-path/', system_config_views.file_path_config_view, name='file_path_config'),
path('system/cleanup/', system_config_views.cleanup_config_view, name='cleanup_config'),
path('system/select-folder/', system_config_views.select_folder_api, name='select_folder_api'),
path('system/cleanup-now/', system_config_views.cleanup_now_view, name='cleanup_now'),
```

## 完整示例

```python
# work_tools/urls.py

from django.urls import path
from work_tools.modules.system_config import views as system_config_views
# ... 其他导入

urlpatterns = [
    # 系统配置模块
    path('system/config/', system_config_views.system_config_view, name='system_config'),
    path('system/file-path/', system_config_views.file_path_config_view, name='file_path_config'),
    path('system/cleanup/', system_config_views.cleanup_config_view, name='cleanup_config'),
    path('system/select-folder/', system_config_views.select_folder_api, name='select_folder_api'),
    path('system/cleanup-now/', system_config_views.cleanup_now_view, name='cleanup_now'),
    
    # ... 其他URL模式
]
```

## 验证步骤

1. **更新URL配置**
   ```bash
   # 编辑 work_tools/urls.py
   # 按照上面的示例更新导入和URL模式
   ```

2. **重启Django服务器**
   ```bash
   python manage.py runserver
   ```

3. **测试所有页面**
   - 访问 http://localhost:8000/system/config/
   - 访问 http://localhost:8000/system/file-path/
   - 访问 http://localhost:8000/system/cleanup/
   - 访问 http://localhost:8000/database-config/

4. **检查功能**
   - ✅ 页面正常加载
   - ✅ 样式正确显示
   - ✅ 表单提交正常
   - ✅ 数据保存成功

## 清理旧文件

确认一切正常后，可以删除以下旧文件：

```bash
# 删除旧的视图文件备份
rm work_tools/views/system_config.py.old

# 删除旧的模板文件（可选，建议先保留一段时间）
# rm work_tools/templates/system_config.html
# rm work_tools/templates/database_config.html
# rm work_tools/templates/file_path_config.html
# rm work_tools/templates/cleanup_config.html
```

## 优势

使用新的模块化结构后：

1. **代码组织更清晰** - 相关文件集中在一起
2. **易于维护** - 修改某个模块不影响其他模块
3. **便于扩展** - 添加新模块时结构一致
4. **减少冲突** - 每个模块有独立的命名空间

## 故障排除

### 问题1: ImportError
```
ImportError: cannot import name 'views' from 'work_tools.modules.system_config'
```

**解决方案**: 确保 `work_tools/modules/system_config/__init__.py` 文件存在且包含正确的导入。

### 问题2: TemplateDoesNotExist
```
TemplateDoesNotExist: modules/system_config/system_config.html
```

**解决方案**: 确保模板文件已正确复制到 `work_tools/templates/modules/system_config/` 目录。

### 问题3: 样式不显示
```
CSS文件404错误
```

**解决方案**: 确保 `work_tools/static/css/system-pages.css` 文件存在，并运行 `python manage.py collectstatic`。

## 需要帮助？

如果遇到问题，请检查：
1. 所有文件是否在正确的位置
2. `__init__.py` 文件是否存在
3. Django服务器是否已重启
4. 浏览器缓存是否已清除
