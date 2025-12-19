# 下拉框配置管理模板路径修复

## 问题描述

用户报告下拉框配置管理页面出现以下问题：
1. 选项内容不显示
2. 缺少搜索功能
3. 缺少分页功能
4. 缺少删除分组按钮

## 根本原因

在模块化重构过程中，视图使用了错误的模板文件：
- **错误的模板**: `modules/system_config/dropdown_config.html` - 这是一个简化版本，缺少很多功能
- **正确的模板**: `dropdown_config.html` - 这是完整版本，包含所有功能

## 修复内容

### 1. 修复视图模板路径

**文件**: `work_tools/modules/system_config/dropdown_config.py`

**修改前**:
```python
return render(request, 'modules/system_config/dropdown_config.html', {
```

**修改后**:
```python
return render(request, 'dropdown_config.html', {
```

### 2. 模板功能对比

#### 错误模板 (`modules/system_config/dropdown_config.html`)
- ❌ 没有搜索框
- ❌ 没有分页控件
- ❌ 没有删除分组按钮
- ❌ 使用错误的变量名 (`options` 而不是 `options_page`)

#### 正确模板 (`dropdown_config.html`)
- ✅ 包含搜索框和搜索功能
- ✅ 包含分组和选项的分页控件
- ✅ 包含删除分组按钮
- ✅ 使用正确的变量名 (`groups_page`, `options_page`)
- ✅ 包含完整的CRUD操作

## 修复的文件

1. `work_tools/modules/system_config/dropdown_config.py` - 修复模板路径（2处）

## 验证步骤

1. 重启 Django 服务器
2. 访问下拉框配置管理页面
3. 验证以下功能：
   - ✅ 分组列表正常显示
   - ✅ 选项列表正常显示
   - ✅ 搜索功能可用
   - ✅ 分页功能可用
   - ✅ 删除分组按钮可见
   - ✅ 所有CRUD操作正常

## 相关文件

- `work_tools/modules/system_config/dropdown_config.py` - 视图文件
- `work_tools/templates/dropdown_config.html` - 正确的模板文件
- `work_tools/templates/modules/system_config/dropdown_config.html` - 错误的简化模板（应该删除或重命名）

## 建议

为避免将来混淆，建议：
1. 删除或重命名 `work_tools/templates/modules/system_config/dropdown_config.html`
2. 或者将完整模板内容复制到 `modules/system_config/dropdown_config.html`，保持模板路径的一致性

## 日期

2024-12-19
