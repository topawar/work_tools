#!/usr/bin/env python
"""
替换模板中的CDN链接为本地静态文件路径
"""

import re
from pathlib import Path

# 模板目录
TEMPLATES_DIR = Path('work_tools/templates')

# CDN链接到本地路径的映射
CDN_REPLACEMENTS = {
    # Bootstrap CSS
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css': "{% static 'vendor/css/bootstrap.min.css' %}",
    
    # Bootstrap JS
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js': "{% static 'vendor/js/bootstrap.bundle.min.js' %}",
    
    # Bootstrap Icons
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css': "{% static 'vendor/css/bootstrap-icons.min.css' %}",
    
    # jQuery
    'https://code.jquery.com/jquery-3.6.0.min.js': "{% static 'vendor/js/jquery-3.6.0.min.js' %}",
    
    # Select2 CSS
    'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css': "{% static 'vendor/css/select2.min.css' %}",
    'https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css': "{% static 'vendor/css/select2-bootstrap-5-theme.min.css' %}",
    
    # Select2 JS
    'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js': "{% static 'vendor/js/select2.min.js' %}",
}


def process_template(file_path):
    """处理单个模板文件"""
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # 检查是否已有 {% load static %}
    has_load_static = '{% load static %}' in content
    
    # 替换CDN链接
    for cdn_url, local_path in CDN_REPLACEMENTS.items():
        content = content.replace(cdn_url, local_path)
    
    # 如果有替换且没有 load static，添加它
    if content != original_content and not has_load_static:
        # 在 <!DOCTYPE html> 或 <html> 后添加 {% load static %}
        if '<!DOCTYPE html>' in content:
            content = content.replace('<!DOCTYPE html>', '<!DOCTYPE html>\n{% load static %}', 1)
        elif '<html' in content:
            # 找到 <html...> 标签结束位置
            match = re.search(r'<html[^>]*>', content)
            if match:
                pos = match.end()
                content = content[:pos] + '\n{% load static %}' + content[pos:]
        else:
            # 在文件开头添加
            content = '{% load static %}\n' + content
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("替换模板中的CDN链接")
    print("=" * 60)
    
    modified_count = 0
    
    # 处理所有HTML模板
    for template_file in TEMPLATES_DIR.glob('*.html'):
        print(f"处理: {template_file.name}...", end=' ')
        if process_template(template_file):
            print("已修改")
            modified_count += 1
        else:
            print("无需修改")
    
    print("\n" + "=" * 60)
    print(f"完成! 修改了 {modified_count} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    main()
