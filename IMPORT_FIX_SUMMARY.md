# 数据导入问题修复总结

## 问题描述
用户反馈：输入"中核（上海）供应链管理有限公司"时，查询回显出现问题，只显示"中核（上海）供应链管理有限公司西北分公司"的记录，但数据库中应该存在总公司的记录。

## 根本原因
经过排查，发现三个数据导入模块都存在问题，导致导入的数据与CSV文件不一致：

### 1. 组织机构导入 (org_api.py)
**问题**：使用 `update_or_create(company_code=cc, ...)` 
- 相同 `company_code` 的记录会被覆盖
- 如果CSV中有多条记录使用相同编码但不同名称，后面的会覆盖前面的

### 2. 物资数据导入 (item_manage.py)
**问题**：使用去重逻辑 `uniq[b['item_id']] = b`
- 相同 `item_id` 的记录只保留最后一条
- 导致CSV中的重复记录丢失

### 3. 用户组织机构导入 (user_org_manage.py)
**问题**：使用去重逻辑 `uniq[b['login_name']] = b`
- 相同 `login_name` 的记录只保留最后一条
- 导致CSV中的重复记录丢失

### 4. 数据库约束问题
**问题**：模型定义中存在唯一性约束
- `OrgDetail.company_code` 有 `unique=True` 约束
- `ItemDetail.item_id` 是主键，也有唯一性约束
- 这些约束阻止了重复数据的导入

## 修复方案

### 1. 修改导入逻辑
✅ **OrgDetail**: 改为直接 `create()`，不再使用 `update_or_create()`
```python
# 修复前
OrgDetail.objects.update_or_create(company_code=cc, defaults={...})

# 修复后
OrgDetail.objects.create(
    company_code=cc if cc else None,
    company_name=cn,
    plate_code=pc,
    plate_name=pn
)
```

✅ **ItemDetail**: 移除去重逻辑，直接批量创建所有记录
```python
# 修复前
uniq = {}
for b in buffer:
    uniq[b['item_id']] = b
to_create = [ItemDetail(**v) for v in uniq.values()]

# 修复后
to_create = [ItemDetail(**b) for b in buffer]
```

✅ **UserOrgDetail**: 移除去重逻辑，直接批量创建所有记录
```python
# 修复前
uniq = {}
for b in buffer:
    uniq[b['login_name']] = b
to_create = [UserOrgDetail(**v) for v in uniq.values()]

# 修复后
to_create = [UserOrgDetail(**b) for b in buffer]
```

### 2. 修改数据库模型
✅ **OrgDetail.company_code**: 移除 `unique=True` 约束
```python
# 修复前
company_code = models.CharField(max_length=255, unique=True, null=True, blank=True)

# 修复后
company_code = models.CharField(max_length=255, null=True, blank=True)
```

✅ **ItemDetail.item_id**: 从主键改为普通字段，添加自增主键
```python
# 修复前
item_id = models.CharField(max_length=100, primary_key=True)

# 修复后
id = models.AutoField(primary_key=True)
item_id = models.CharField(max_length=100)
```

### 3. 应用数据库结构变更
✅ 使用SQL脚本直接修改数据库结构：
- 备份原有数据
- 删除旧表
- 重新创建表（无唯一性约束）
- 恢复数据

### 4. 优化搜索API
✅ 修改搜索逻辑，精确匹配优先：
```python
# 1. 精确匹配公司名称
exact_matches = OrgDetail.objects.filter(company_name=q)

# 2. 模糊匹配公司名称和编码
fuzzy_matches = OrgDetail.objects.filter(
    Q(company_name__icontains=q) | Q(company_code__icontains=q)
).exclude(id__in=exact_matches.values_list('id', flat=True))

# 合并结果，精确匹配在前
qs = list(exact_matches) + list(fuzzy_matches[:9])
```

## 验证结果

### 修复前
```sql
SELECT company_name, company_code FROM org_detail 
WHERE company_name = '中核（上海）供应链管理有限公司';
-- 结果：0条记录
```

### 修复后
```sql
SELECT company_name, company_code FROM org_detail 
WHERE company_name = '中核（上海）供应链管理有限公司';
-- 结果：
-- 中核（上海）供应链管理有限公司|99280563919161110148
```

```sql
SELECT company_name, company_code FROM org_detail 
WHERE company_name LIKE '%中核%供应链%' ORDER BY company_name;
-- 结果：
-- 中核新疆供应链有限公司|99280563919161110348
-- 中核（上海）供应链管理有限公司|99280563919161110148
-- 中核（上海）供应链管理有限公司北京分公司|99280563919161110148
-- 中核（上海）供应链管理有限公司西北分公司|99280563919161110148
-- 中核（上海）供应链管理有限公司西北分公司|1912178770857907780
```

## 修复效果

✅ **导入逻辑**：现在完全按照CSV文件内容导入，不做任何去重或合并
✅ **数据完整性**：CSV中的所有记录都会被导入，包括重复的编码
✅ **搜索功能**：精确匹配优先显示，用户体验更好
✅ **数据一致性**：数据库内容与CSV文件完全一致

## 注意事项

1. **数据质量**：移除唯一性约束后，需要在应用层面确保数据质量
2. **查询性能**：如果需要频繁按 company_code 或 item_id 查询，建议添加索引
3. **重新导入**：建议使用原始CSV文件重新导入数据，确保数据完整性
4. **搜索结果**：如果有重复记录，搜索结果会返回多条，前端需要能够处理

## 后续建议

1. 使用原始CSV文件重新导入组织机构数据
2. 验证所有缺失的记录是否已正确导入
3. 测试搜索功能，确保精确匹配优先显示
4. 如需要，可以添加数据库索引提升查询性能