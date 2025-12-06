import openpyxl

# 创建测试Excel文件
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "模板"

# 添加表头
headers = [
    "采购方案编号", "询价单编号", "定标结果编号",
    "新起草单位ID", "新起草单位名称",
    "新签约主体ID", "新签约主体名称",
    "原起草单位ID", "原起草单位名称",
    "原签约主体ID", "原签约主体名称"
]
ws.append(headers)

# 添加数据行
row1 = [
    "ZCKG-CGFA-25-01214", "ZCKG-XJD-25-01303", "ZCKG-NQ-25-00987",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司"
]
ws.append(row1)

row2 = [
    "ZCKG-CGFA-25-01211", "ZCKG-XJD-25-01299", "ZCKG-NQ-25-00972",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司",
    "", "中核（广东江门）投资有限公司"
]
ws.append(row2)

# 保存文件
filepath = r'd:\Project\pyProject\work_tools\unit_change_template.xlsx'
wb.save(filepath)
print(f"测试Excel文件已创建: {filepath}")
