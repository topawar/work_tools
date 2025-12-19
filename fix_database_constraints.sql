-- 修复数据库约束的SQL脚本
-- 移除 org_detail.company_code 的 UNIQUE 约束
-- 修改 item_detail 的主键结构

.headers on
.mode column

-- 1. 备份现有数据
CREATE TABLE org_detail_backup AS SELECT * FROM org_detail;
CREATE TABLE item_detail_backup AS SELECT * FROM item_detail;

SELECT '=== 备份完成 ===' as info;

-- 2. 删除原表
DROP TABLE org_detail;
DROP TABLE item_detail;

-- 3. 重新创建 org_detail 表（无 UNIQUE 约束）
CREATE TABLE org_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_code VARCHAR(255) NULL,
    company_name VARCHAR(255) NULL,
    plate_code VARCHAR(255) NULL,
    plate_name VARCHAR(255) NULL
);

-- 4. 重新创建 item_detail 表（item_id 不再是主键）
CREATE TABLE item_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id VARCHAR(100),
    item_name VARCHAR(1000),
    category VARCHAR(100),
    item_uom VARCHAR(25),
    purc_type VARCHAR(10)
);

SELECT '=== 表结构重建完成 ===' as info;

-- 5. 恢复数据
INSERT INTO org_detail (company_code, company_name, plate_code, plate_name)
SELECT company_code, company_name, plate_code, plate_name FROM org_detail_backup;

INSERT INTO item_detail (item_id, item_name, category, item_uom, purc_type)
SELECT item_id, item_name, category, item_uom, purc_type FROM item_detail_backup;

SELECT '=== 数据恢复完成 ===' as info;

-- 6. 验证结果
SELECT 'org_detail 记录数: ' || COUNT(*) as info FROM org_detail;
SELECT 'item_detail 记录数: ' || COUNT(*) as info FROM item_detail;

-- 7. 显示新的表结构
.schema org_detail
.schema item_detail

-- 8. 清理备份表
DROP TABLE org_detail_backup;
DROP TABLE item_detail_backup;

SELECT '=== 修复完成 ===' as info;