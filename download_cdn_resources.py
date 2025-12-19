#!/usr/bin/env python
"""
下载CDN资源到本地静态文件目录
"""

import os
import urllib.request
from pathlib import Path

# 静态文件目录
STATIC_DIR = Path('work_tools/static/vendor')

# 需要下载的CDN资源
CDN_RESOURCES = {
    # Bootstrap CSS
    'css/bootstrap.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    
    # Bootstrap JS
    'js/bootstrap.bundle.min.js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    
    # Bootstrap Icons CSS
    'css/bootstrap-icons.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    
    # jQuery
    'js/jquery-3.6.0.min.js': 'https://code.jquery.com/jquery-3.6.0.min.js',
    
    # Select2 CSS
    'css/select2.min.css': 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
    'css/select2-bootstrap-5-theme.min.css': 'https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css',
    
    # Select2 JS
    'js/select2.min.js': 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
}

# Bootstrap Icons 字体文件
BOOTSTRAP_ICONS_FONTS = {
    'fonts/bootstrap-icons.woff': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff',
    'fonts/bootstrap-icons.woff2': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2',
}


def download_file(url, dest_path):
    """下载文件"""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"下载: {url}")
    print(f"  -> {dest_path}")
    
    try:
        # 设置请求头，模拟浏览器
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            
        with open(dest_path, 'wb') as f:
            f.write(content)
            
        print(f"  完成 ({len(content)} bytes)")
        return True
    except Exception as e:
        print(f"  失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("下载CDN资源到本地")
    print("=" * 60)
    
    # 创建目录
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    # 下载主要资源
    print("\n下载主要资源...")
    for local_path, url in CDN_RESOURCES.items():
        dest = STATIC_DIR / local_path
        if download_file(url, dest):
            success_count += 1
        else:
            fail_count += 1
    
    # 下载字体文件
    print("\n下载Bootstrap Icons字体...")
    for local_path, url in BOOTSTRAP_ICONS_FONTS.items():
        dest = STATIC_DIR / local_path
        if download_file(url, dest):
            success_count += 1
        else:
            fail_count += 1
    
    # 修复bootstrap-icons.css中的字体路径
    print("\n修复字体路径...")
    icons_css_path = STATIC_DIR / 'css' / 'bootstrap-icons.min.css'
    if icons_css_path.exists():
        content = icons_css_path.read_text(encoding='utf-8')
        # 修改字体路径为相对路径
        content = content.replace('./fonts/', '../fonts/')
        icons_css_path.write_text(content, encoding='utf-8')
        print("  bootstrap-icons.min.css 字体路径已修复")
    
    print("\n" + "=" * 60)
    print(f"完成! 成功: {success_count}, 失败: {fail_count}")
    print("=" * 60)
    
    if fail_count > 0:
        print("\n注意: 部分文件下载失败，请手动下载或检查网络连接")


if __name__ == '__main__':
    main()
