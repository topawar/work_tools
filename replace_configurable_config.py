"""替换可配置表管理页面为新UI"""
import shutil

# 备份原文件（如果还没备份）
try:
    shutil.copy(
        'work_tools/templates/configurable_config.html',
        'work_tools/templates/configurable_config.html.backup2'
    )
    print("✅ 已备份原文件")
except Exception as e:
    print(f"备份失败: {e}")

# 读取旧文件内容以保留模态框和JavaScript
with open('work_tools/templates/configurable_config.html.old', 'r', encoding='utf-8') as f:
    old_content = f.read()

# 新的HTML内容（完整版本）
new_html = '''<!DOCTYPE html>
{% load static %}
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>可配置表管理 - Work Tools</title>
    <link rel="stylesheet" href="{% static 'css/system-pages.css' %}">
    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap-icons.min.css' %}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .config-layout {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 24px;
            margin-top: 24px;
        }
        .table-list {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            max-height: calc(100vh - 200px);
            overflow-y: auto;
        }
        .table-item {
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .table-item:hover, .table-item.active {
            border-color: #2563eb;
            background: #eff6ff;
        }
        .table-display-name {
            font-weight: 600;
            color: #111827;
            margin-bottom: 4px;
        }
        .table-code {
            font-size: 12px;
            color: #6b7280;
            font-family: 'Consolas', monospace;
        }
        .list-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e5e7eb;
        }
        .list-title {
            font-size: 16px;
            font-weight: 600;
            color: #111827;
        }
        @media (max-width: 768px) {
            .config-layout {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">
            <i class="bi bi-arrow-left"></i>
            返回首页
        </a>

        <div class="page-header">
            <h1 class="page-title">
                <i class="bi bi-table"></i>
                可配置表管理
            </h1>
            <p class="page-desc">配置通用数据修改页面的表和字段信息</p>
        </div>

        {% if message %}
        <div class="alert alert-success">
            <i class="bi bi-check-circle-fill"></i>
            <span>{{ message }}</span>
        </div>
        {% endif %}
        
        {% if error %}
        <div class="alert alert-error">
            <i class="bi bi-exclamation-circle-fill"></i>
            <span>{{ error }}</span>
        </div>
        {% endif %}

        <div class="config-layout">
            <!-- 左侧：表配置列表 -->
            <div class="table-list">
                <div class="list-header">
                    <h5 class="list-title">表配置列表</h5>
                    <button type="button" class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#addTableModal">
                        <i class="bi bi-plus-circle"></i>
                        添加
                    </button>
                </div>

                <!-- 搜索框 -->
                <div class="form-group" style="margin-bottom: 16px;">
                    <input type="text" class="form-input" id="searchInput" placeholder="搜索表名或编码..." 
                           onkeyup="filterTables()">
                </div>

                <div id="tableListContainer">
                    {% if tables %}
                        {% for table in tables %}
                        <div class="table-item {% if selected_table and table.id == selected_table.id %}active{% endif %}" 
                             onclick="location.href='?table_id={{ table.id }}'"
                             data-search="{{ table.display_name|lower }} {{ table.table_code|lower }} {{ table.table_name|lower }}">
                            <div class="table-display-name">{{ table.display_name }}</div>
                            <div class="table-code">{{ table.table_code }} ({{ table.table_name }})</div>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div style="text-align: center; padding: 30px 10px; color: #6b7280;">
                            <i class="bi bi-inbox" style="font-size: 48px; display: block; margin-bottom: 12px;"></i>
                            暂无表配置
                        </div>
                    {% endif %}
                </div>
                
                <div id="noResults" style="text-align: center; padding: 30px 10px; color: #6b7280; display: none;">
                    未找到匹配的表配置
                </div>
            </div>

            <!-- 右侧：字段配置管理 -->
            <div class="config-panel">
                {% if selected_table %}
                <div class="panel-header">
                    <div>
                        <h2 class="panel-title">
                            <i class="bi bi-table"></i>
                            {{ selected_table.display_name }}
                        </h2>
                        <p class="panel-subtitle">{{ selected_table.description }}</p>
                    </div>
                </div>

                <div class="panel-body" style="padding: 0;">
                    <div style="padding: 16px 24px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 8px;">
                        <button type="button" class="btn btn-outline btn-sm" data-bs-toggle="modal" data-bs-target="#editTableModal">
                            <i class="bi bi-pencil"></i>
                            编辑表配置
                        </button>
                        <form method="post" action="/configurable-config/table/toggle/" style="display: inline;">
                            {% csrf_token %}
                            <input type="hidden" name="table_id" value="{{ selected_table.id }}">
                            <button type="submit" class="btn {% if selected_table.is_active %}btn-secondary{% else %}btn-success{% endif %} btn-sm">
                                <i class="bi bi-{% if selected_table.is_active %}pause-circle{% else %}play-circle{% endif %}"></i>
                                {% if selected_table.is_active %}禁用表{% else %}启用表{% endif %}
                            </button>
                        </form>
                    </div>

                    <!-- 标签页 -->
                    <ul class="nav nav-tabs" role="tablist" style="padding: 0 24px; margin-top: 16px;">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="update-tab" data-bs-toggle="tab" data-bs-target="#update-fields" type="button">
                                <i class="bi bi-pencil-square"></i> 修改字段配置
                            </button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="query-tab" data-bs-toggle="tab" data-bs-target="#query-fields" type="button">
                                <i class="bi bi-search"></i> 查询字段配置
                            </button>
                        </li>
                    </ul>

                    <div class="tab-content">
'''

# 从旧文件中提取修改字段和查询字段的表格部分
# 这里保留原有的表格结构和模态框
import re

# 提取修改字段表格
update_fields_match = re.search(
    r'<!-- 修改字段配置 -->.*?</div>\s*<!-- 查询字段配置 -->',
    old_content,
    re.DOTALL
)

# 提取查询字段表格
query_fields_match = re.search(
    r'<!-- 查询字段配置 -->.*?</div>\s*</div>\s*{% else %}',
    old_content,
    re.DOTALL
)

# 提取所有模态框
modals_match = re.search(
    r'<!-- 添加表配置模态框 -->.*?{% endif %}\s*{% endblock %}',
    old_content,
    re.DOTALL
)

# 提取JavaScript
js_match = re.search(
    r'{% block extra_js %}.*?{% endblock %}',
    old_content,
    re.DOTALL
)

if update_fields_match:
    new_html += update_fields_match.group(0)
else:
    print("⚠️ 未找到修改字段配置部分")

if query_fields_match:
    new_html += query_fields_match.group(0)
else:
    print("⚠️ 未找到查询字段配置部分")

new_html += '''
                    </div>
                </div>
                {% else %}
                <div class="panel-body">
                    <div style="text-align: center; padding: 60px 20px; color: #6b7280;">
                        <i class="bi bi-arrow-left-circle" style="font-size: 64px; display: block; margin-bottom: 16px;"></i>
                        <p style="font-size: 16px; margin: 0;">请从左侧选择一个表配置</p>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
'''

if modals_match:
    new_html += modals_match.group(0).replace('{% endblock %}', '')
else:
    print("⚠️ 未找到模态框部分")

if js_match:
    new_html += '\n' + js_match.group(0)
else:
    print("⚠️ 未找到JavaScript部分")

new_html += '''
</body>
</html>
'''

# 写入新文件
with open('work_tools/templates/configurable_config.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("✅ 已替换为新UI版本")
print("📝 原文件备份为: configurable_config.html.old 和 configurable_config.html.backup2")
