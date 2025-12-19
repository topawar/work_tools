-- 检查组织机构数据的SQL脚本

-- 1. 检查中核供应链相关的所有记录
.headers on
.mode column
SELECT '=== 中核供应链相关记录 ===' as info;
SELECT company_name, company_code 
FROM org_detail 
WHERE company_name LIKE '%中核%' AND company_name LIKE '%供应链%'
ORDER BY company_name;

-- 2. 检查是否存在精确匹配的记录
SELECT '=== 精确匹配检查 ===' as info;
SELECT company_name, company_code 
FROM org_detail 
WHERE company_name = '中核（上海）供应链管理有限公司';

-- 3. 检查重复的company_code
SELECT '=== 重复编码检查 ===' as info;
SELECT company_code, COUNT(*) as count
FROM org_detail 
WHERE company_code IS NOT NULL
GROUP BY company_code 
HAVING COUNT(*) > 1;

-- 4. 检查可能的数据问题
SELECT '=== 西北分公司相关记录 ===' as info;
SELECT company_name, company_code
FROM org_detail 
WHERE company_name LIKE '%西北分公司%';

-- 5. 统计信息
SELECT '=== 统计信息 ===' as info;
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT company_code) as unique_codes,
    COUNT(DISTINCT company_name) as unique_names
FROM org_detail;