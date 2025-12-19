import os

# 读取备份文件
with open('work_tools/templates/configurable_config.html.old', 'r', encoding='utf-8') as f:
    content = f.read()

# 写入目标文件（覆盖）
with open('work_tools/templates/configurable_config.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已恢复可配置表管理页面")
print("📝 该页面保持原有样式（使用 modern-ui.css）")
