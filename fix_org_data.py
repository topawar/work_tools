#!/usr/bin/env python
"""
组织机构数据修复脚本
"""
import sqlite3

def fix_missing_parent_company():
    """修复缺失的总公司记录"""
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    try:
        # 检查是否存在中核（上海）供应链管理有限公司
        cursor.execute("""
            SELECT COUNT(*) FROM org_detail 
            WHERE company_name = '中核（上海）供应链管理有限公司'
        """)
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("发现缺失的总公司记录，正在添加...")
            
            # 从西北分公司记录中获取板块信息
            cursor.execute("""
                SELECT plate_code, plate_name FROM org_detail 
                WHERE company_name = '中核（上海）供应链管理有限公司西北分公司'
                LIMIT 1
            """)
            plate_info = cursor.fetchone()
            
            if plate_info:
                plate_code, plate_name = plate_info
                
                # 生成一个新的company_code（基于现有的编码规律）
                # 这里使用一个临时编码，实际应该从你的数据源获取正确编码
                new_company_code = "ZHONGHE_SHANGHAI_SUPPLY_CHAIN"
                
                # 插入总公司记录
                cursor.execute("""
                    INSERT INTO org_detail (company_code, company_name, plate_code, plate_name)
                    VALUES (?, ?, ?, ?)
                """, (new_company_code, '中核（上海）供应链管理有限公司', plate_code, plate_name))
                
                print(f"已添加总公司记录: 中核（上海）供应链管理有限公司 (编码: {new_company_code})")
            else:
                print("无法获取板块信息，跳过添加")
        else:
            print("总公司记录已存在")
        
        # 检查重复记录
        cursor.execute("""
            SELECT company_name, COUNT(*) as cnt 
            FROM org_detail 
            GROUP BY company_name 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"\n发现 {len(duplicates)} 个重复名称的记录:")
            for name, count in duplicates:
                print(f"  - {name}: {count} 条记录")
                
                # 显示重复记录的详细信息
                cursor.execute("""
                    SELECT id, company_code FROM org_detail 
                    WHERE company_name = ?
                """, (name,))
                records = cursor.fetchall()
                for record_id, code in records:
                    print(f"    ID: {record_id}, 编码: {code}")
        
        conn.commit()
        print("\n修复完成!")
        
    except Exception as e:
        print(f"修复过程中出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("开始修复组织机构数据...")
    fix_missing_parent_company()