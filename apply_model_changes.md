# 数据库模型更改说明

## 问题根源
导入逻辑存在以下问题：
1. **OrgDetail**: 使用 `update_or_create` 导致相同 `company_code` 的记录被覆盖
2. **ItemDetail**: 使用去重逻辑导致相同 `item_id` 的记录只保留最后一条
3. **UserOrgDetail**: 使用去重逻辑导致相同 `login_name` 的记录只保留最后一条

## 已完成的修复

### 1. 修改导入逻辑
- ✅ **OrgDetail**: 改为直接 `create()`，不再使用 `update_or_create()`
- ✅ **ItemDetail**: 移除去重逻辑，直接批量创建所有记录
- ✅ **UserOrgDetail**: 移除去重逻辑，直接批量创建所有记录

### 2. 修改数据库模型
- ✅ **OrgDetail.company_code**: 移除 `unique=True` 约束
- ✅ **ItemDetail.item_id**: 从主键改为普通字段，添加自增主键

## 需要执行的数据库迁移

由于修改了模型定义，需要执行以下步骤：

### 方法1：使用Django迁移（推荐）
```bash
# 生成迁移文件
python manage.py makemigrations work_tools

# 应用迁移
python manage.py migrate work_tools
```

### 方法2：手动修改数据库（如果Django迁移失败）
```sql
-- 1. 备份数据
CREATE TABLE org_detail_backup AS SELECT * FROM org_detail;
CREATE TABLE item_detail_backup AS SELECT * FROM item_detail;

-- 2. 删除旧表
DROP TABLE org_detail;
DROP TABLE item_detail;

-- 3. 重新创建表（无唯一性约束）
CREATE TABLE org_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_code VARCHAR(255),
    company_name VARCHAR(255),
    plate_code VARCHAR(255),
    plate_name VARCHAR(255)
);

CREATE TABLE item_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id VARCHAR(100),
    item_name VARCHAR(1000),
    category VARCHAR(100),
    item_uom VARCHAR(25),
    purc_type VARCHAR(10)
);

-- 4. 恢复数据
INSERT INTO org_detail (company_code, company_name, plate_code, plate_name)
SELECT company_code, company_name, plate_code, plate_name FROM org_detail_backup;

INSERT INTO item_detail (item_id, item_name, category, item_uom, purc_type)
SELECT item_id, item_name, category, item_uom, purc_type FROM item_detail_backup;

-- 5. 删除备份表
DROP TABLE org_detail_backup;
DROP TABLE item_detail_backup;
```

## 验证修复

修复后，重新导入CSV文件，数据库内容应该与CSV文件完全一致，包括：
- 允许重复的 company_code
- 允许重复的 item_id
- 允许重复的 login_name
- 所有CSV行都会被导入，不会被覆盖或去重

## 注意事项

1. **数据完整性**: 移除唯一性约束后，需要在应用层面确保数据质量
2. **查询性能**: 如果需要频繁按 company_code 或 item_id 查询，建议添加索引：
   ```sql
   CREATE INDEX idx_org_company_code ON org_detail(company_code);
   CREATE INDEX idx_item_item_id ON item_detail(item_id);
   ```
3. **搜索API**: 如果有重复记录，搜索结果会返回多条，前端需要能够处理这种情况