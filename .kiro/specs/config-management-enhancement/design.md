# 配置管理功能增强设计文档

## Overview

本设计文档描述了配置管理功能增强的技术实现方案，包括下拉框配置管理和可配置表管理的搜索、分页、删除等功能。设计遵循现有代码架构，采用 Django 后端 + 前端 JavaScript 的实现方式，确保与现有系统的一致性。

## Architecture

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Templates)                     │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │ dropdown_config.html │    │ configurable_config.html │   │
│  │  - 搜索框            │    │  - 表列表搜索            │   │
│  │  - 分页控件          │    │  - 字段列表搜索          │   │
│  │  - 分组/选项列表     │    │  - 字段分页控件          │   │
│  └──────────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        视图层 (Views)                         │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │ dropdown_config.py   │    │ configurable_config.py   │   │
│  │  - 分页查询          │    │  - 字段分页查询          │   │
│  │  - 搜索过滤          │    │  - 字段搜索过滤          │   │
│  │  - 删除分组          │    │  - 现有CRUD操作          │   │
│  └──────────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        模型层 (Models)                        │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │ DropdownGroup        │    │ ConfigurableTable        │   │
│  │ DropdownOption       │    │ ConfigurableField        │   │
│  └──────────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

- **后端**: Django 3.x
- **前端**: 原生 JavaScript + Bootstrap 5
- **数据库**: SQLite (现有)
- **分页**: Django Paginator
- **缓存**: Django Cache Framework

## Components and Interfaces

### 1. 下拉框配置管理组件

#### 1.1 后端视图增强

**dropdown_config_view** 函数修改：
```python
def dropdown_config_view(request):
    # 获取搜索关键词
    search_query = request.GET.get('search', '').strip()
    
    # 获取分页参数
    page = request.GET.get('page', 1)
    per_page = 10
    
    # 查询分组（支持搜索）
    groups_query = DropdownGroup.objects.all()
    if search_query:
        groups_query = groups_query.filter(
            Q(group_name__icontains=search_query) |
            Q(group_code__icontains=search_query)
        )
    
    # 分页
    paginator = Paginator(groups_query.order_by('group_code'), per_page)
    groups_page = paginator.get_page(page)
    
    # 获取选项（支持搜索）
    options_query = DropdownOption.objects.filter(group=selected_group)
    if search_query:
        options_query = options_query.filter(
            Q(option_label__icontains=search_query) |
            Q(option_code__icontains=search_query)
        )
    
    # 选项分页
    options_paginator = Paginator(options_query.order_by('sort_order'), per_page)
    options_page = options_paginator.get_page(request.GET.get('option_page', 1))
```

**新增删除分组功能**：
```python
@require_POST
def dropdown_group_delete(request):
    """删除配置分组及其所有选项"""
    group_id = request.POST.get('group_id')
    group = get_object_or_404(DropdownGroup, id=group_id)
    
    # 删除分组（级联删除选项）
    group_code = group.group_code
    group.delete()
    
    # 清除缓存
    clear_dropdown_cache(group_code)
    
    return redirect('/dropdown-config/?message=删除分组成功')
```

#### 1.2 前端模板增强

**搜索框组件**：
```html
<div class="search-box">
  <input type="text" 
         id="searchInput" 
         class="form-control" 
         placeholder="搜索分组名称、编码或选项..."
         value="{{ search_query }}">
  <button type="button" id="clearSearch" class="btn btn-sm">×</button>
</div>
```

**分页控件组件**：
```html
<nav aria-label="分页导航">
  <ul class="pagination">
    {% if page_obj.has_previous %}
    <li class="page-item">
      <a class="page-link" href="?page={{ page_obj.previous_page_number }}&search={{ search_query }}">上一页</a>
    </li>
    {% endif %}
    
    <li class="page-item active">
      <span class="page-link">第 {{ page_obj.number }} / {{ page_obj.paginator.num_pages }} 页</span>
    </li>
    
    {% if page_obj.has_next %}
    <li class="page-item">
      <a class="page-link" href="?page={{ page_obj.next_page_number }}&search={{ search_query }}">下一页</a>
    </li>
    {% endif %}
  </ul>
</nav>
```

**JavaScript 搜索逻辑**：
```javascript
// 防抖搜索
let searchTimeout;
document.getElementById('searchInput').addEventListener('input', function() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function() {
    const query = document.getElementById('searchInput').value;
    window.location.href = `?search=${encodeURIComponent(query)}`;
  }, 500);
});
```

### 2. 可配置表管理组件

#### 2.1 后端视图增强

**configurable_config_view** 函数修改：
```python
def configurable_config_view(request):
    # 获取字段搜索关键词
    field_search = request.GET.get('field_search', '').strip()
    
    # 查询字段分页
    update_fields_query = ConfigurableField.objects.filter(
        table=selected_table,
        field_type='update'
    )
    if field_search:
        update_fields_query = update_fields_query.filter(
            Q(field_name__icontains=field_search) |
            Q(display_name__icontains=field_search)
        )
    
    # 修改字段分页
    update_paginator = Paginator(
        update_fields_query.order_by('sort_order', 'field_name'), 
        10
    )
    update_fields_page = update_paginator.get_page(
        request.GET.get('update_page', 1)
    )
    
    # 查询字段分页（类似逻辑）
    query_fields_query = ConfigurableField.objects.filter(
        table=selected_table,
        field_type='query'
    )
    if field_search:
        query_fields_query = query_fields_query.filter(
            Q(field_name__icontains=field_search) |
            Q(display_name__icontains=field_search)
        )
    
    query_paginator = Paginator(
        query_fields_query.order_by('sort_order', 'field_name'), 
        10
    )
    query_fields_page = query_paginator.get_page(
        request.GET.get('query_page', 1)
    )
```

#### 2.2 前端模板增强

**字段搜索框**：
```html
<div class="field-search-box">
  <input type="text" 
         id="fieldSearchInput" 
         class="form-control form-control-sm" 
         placeholder="搜索字段名或显示名称..."
         value="{{ field_search }}">
</div>
```

**字段列表分页**：
```html
<!-- 修改字段分页 -->
<nav aria-label="修改字段分页">
  <ul class="pagination pagination-sm">
    {% if update_fields_page.has_previous %}
    <li class="page-item">
      <a class="page-link" href="?table_id={{ selected_table.id }}&update_page={{ update_fields_page.previous_page_number }}&field_search={{ field_search }}">上一页</a>
    </li>
    {% endif %}
    
    <li class="page-item active">
      <span class="page-link">{{ update_fields_page.number }} / {{ update_fields_page.paginator.num_pages }}</span>
    </li>
    
    {% if update_fields_page.has_next %}
    <li class="page-item">
      <a class="page-link" href="?table_id={{ selected_table.id }}&update_page={{ update_fields_page.next_page_number }}&field_search={{ field_search }}">下一页</a>
    </li>
    {% endif %}
  </ul>
</nav>
```

## Data Models

现有模型无需修改，仅在视图层添加查询逻辑。

### DropdownGroup 模型
```python
class DropdownGroup(models.Model):
    group_code = models.CharField(max_length=50, unique=True)
    group_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### DropdownOption 模型
```python
class DropdownOption(models.Model):
    group = models.ForeignKey(DropdownGroup, on_delete=models.CASCADE)
    option_code = models.CharField(max_length=50)
    option_label = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    remark = models.TextField(blank=True)
```

### ConfigurableField 模型
```python
class ConfigurableField(models.Model):
    table = models.ForeignKey(ConfigurableTable, on_delete=models.CASCADE)
    field_type = models.CharField(max_length=10)  # 'update' or 'query'
    field_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20)
    is_required = models.BooleanField(default=False)
    is_nullable = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
```

## Error Handling

### 搜索无结果处理
```python
if not groups_page.object_list and search_query:
    context['no_results'] = True
    context['search_query'] = search_query
```

### 分页越界处理
```python
try:
    page_obj = paginator.get_page(page)
except (EmptyPage, PageNotAnInteger):
    page_obj = paginator.get_page(1)
```

### 删除操作错误处理
```python
try:
    group.delete()
except ProtectedError:
    return redirect(f'/dropdown-config/?error=该分组正在被使用，无法删除')
except Exception as e:
    logger.error(f"删除分组失败: {e}")
    return redirect(f'/dropdown-config/?error=删除失败: {str(e)}')
```

## Testing Strategy

### 单元测试

**测试搜索功能**：
- 测试分组名称搜索
- 测试分组编码搜索
- 测试选项标签搜索
- 测试选项编码搜索
- 测试空搜索结果

**测试分页功能**：
- 测试第一页显示
- 测试最后一页显示
- 测试页码越界处理
- 测试每页10条记录

**测试删除功能**：
- 测试删除空分组
- 测试删除包含选项的分组（级联删除）
- 测试删除不存在的分组
- 测试删除后缓存清理

### 集成测试

**测试搜索+分页组合**：
- 搜索结果的分页显示
- 搜索状态下的页码切换
- 清空搜索后的分页恢复

**测试UI交互**：
- 搜索框输入防抖
- 分页链接点击
- 删除确认对话框
- 成功/错误提示显示

## Performance Considerations

### 数据库查询优化

1. **使用 select_related 减少查询次数**：
```python
groups = DropdownGroup.objects.select_related().all()
options = DropdownOption.objects.select_related('group').filter(group=selected_group)
```

2. **添加数据库索引**：
```python
class Meta:
    indexes = [
        models.Index(fields=['group_name']),
        models.Index(fields=['group_code']),
        models.Index(fields=['option_label']),
    ]
```

### 前端性能优化

1. **搜索防抖**：500ms 延迟，避免频繁请求
2. **懒加载**：仅加载当前页数据，不加载全部数据
3. **数据库查询优化**：使用 select_related 和 prefetch_related 减少查询次数

## UI/UX Design

### 统一的分页组件样式

```css
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  gap: 5px;
}

.pagination .page-item {
  list-style: none;
}

.pagination .page-link {
  padding: 6px 12px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  color: #0d6efd;
  text-decoration: none;
  transition: all 0.2s;
}

.pagination .page-link:hover {
  background: #e9ecef;
}

.pagination .page-item.active .page-link {
  background: #0d6efd;
  color: white;
  border-color: #0d6efd;
}
```

### 统一的搜索框样式

```css
.search-box {
  position: relative;
  margin-bottom: 15px;
}

.search-box input {
  padding-right: 35px;
}

.search-box .btn {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: none;
  color: #6c757d;
  font-size: 20px;
  line-height: 1;
  padding: 0;
  width: 25px;
  height: 25px;
}
```

### 删除确认对话框

```javascript
function confirmDelete(type, name) {
  return confirm(`确定要删除${type} "${name}" 吗？\n\n此操作不可恢复！`);
}
```

## Implementation Notes

### 实现顺序

1. **Phase 1**: 下拉框配置管理搜索功能
2. **Phase 2**: 下拉框配置管理分页功能
3. **Phase 3**: 下拉框配置管理删除分组功能
4. **Phase 4**: 可配置表管理字段搜索功能
5. **Phase 5**: 可配置表管理字段分页功能
6. **Phase 6**: UI 统一化和优化

### 向后兼容性

- 所有新增参数使用默认值，确保不影响现有功能
- 搜索参数为空时，显示全部数据（现有行为）
- 分页参数缺失时，默认显示第一页

### 代码复用

创建共享的分页和搜索组件：
```python
# work_tools/utils/pagination_helper.py
def paginate_queryset(queryset, page, per_page=10):
    """通用分页辅助函数"""
    paginator = Paginator(queryset, per_page)
    try:
        return paginator.get_page(page)
    except (EmptyPage, PageNotAnInteger):
        return paginator.get_page(1)

def filter_by_search(queryset, search_query, fields):
    """通用搜索过滤辅助函数"""
    if not search_query:
        return queryset
    
    from django.db.models import Q
    q_objects = Q()
    for field in fields:
        q_objects |= Q(**{f'{field}__icontains': search_query})
    
    return queryset.filter(q_objects)
```
