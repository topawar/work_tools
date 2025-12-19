import shutil
import os

# 强制复制，不询问
src = 'work_tools/templates/configurable_config.html.old'
dst = 'work_tools/templates/configurable_config.html'

# 删除目标文件
if os.path.exists(dst):
    os.remove(dst)
    print(f"✅ 已删除损坏的文件: {dst}")

# 复制备份文件
shutil.copy(src, dst)
print(f"✅ 已从备份恢复: {src} -> {dst}")
print("\n📝 可配置表管理页面已恢复为原样")
print("💡 建议: 该页面功能复杂，保持原有样式即可")
