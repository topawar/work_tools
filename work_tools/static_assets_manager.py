"""
静态资源管理器模块
负责管理静态文件的收集、验证和服务功能
"""

import os
import shutil
import hashlib
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import mimetypes


class StaticAssetsManager:
    """静态资源管理器类"""
    
    def __init__(self, static_root: str, templates_root: str, source_static_dirs: Optional[List[str]] = None):
        """
        初始化静态资源管理器
        
        Args:
            static_root: 静态文件根目录
            templates_root: 模板文件根目录
            source_static_dirs: 源静态文件目录列表
        """
        self.static_root = os.path.abspath(static_root)
        self.templates_root = os.path.abspath(templates_root)
        self.source_static_dirs = source_static_dirs or []
        self.logger = logging.getLogger(__name__)
        
        # 支持的静态文件类型
        self.supported_extensions = {
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.woff', '.woff2', '.ttf', '.eot', '.otf', '.map', '.json'
        }
        
        # 支持的模板文件类型
        self.template_extensions = {'.html', '.htm', '.txt', '.xml'}
        
        # 文件清单缓存
        self.assets_manifest = {}
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.static_root, exist_ok=True)
        os.makedirs(self.templates_root, exist_ok=True)
        
        # 创建常见的静态文件子目录
        common_dirs = ['css', 'js', 'images', 'fonts', 'admin']
        for dir_name in common_dirs:
            os.makedirs(os.path.join(self.static_root, dir_name), exist_ok=True)
    
    def collect_static_files(self, source_dirs: Optional[List[str]] = None) -> bool:
        """
        收集静态文件到指定目录
        
        Args:
            source_dirs: 源目录列表，如果为None则使用初始化时的目录
            
        Returns:
            bool: 收集是否成功
        """
        try:
            dirs_to_scan = source_dirs or self.source_static_dirs
            
            if not dirs_to_scan:
                # 如果没有指定源目录，尝试从Django项目结构中查找
                dirs_to_scan = self._discover_static_dirs()
            
            collected_files = 0
            
            for source_dir in dirs_to_scan:
                if not os.path.exists(source_dir):
                    self.logger.warning(f"源目录不存在: {source_dir}")
                    continue
                
                files_count = self._copy_static_files(source_dir, self.static_root)
                collected_files += files_count
                self.logger.info(f"从 {source_dir} 收集了 {files_count} 个静态文件")
            
            # 生成文件清单
            self._generate_manifest()
            
            self.logger.info(f"静态文件收集完成，总共收集了 {collected_files} 个文件")
            return True
            
        except Exception as e:
            self.logger.error(f"收集静态文件失败: {e}")
            return False
    
    def _discover_static_dirs(self) -> List[str]:
        """自动发现Django项目中的静态文件目录"""
        static_dirs = []
        
        # 查找work_tools/static目录
        work_tools_static = os.path.join(os.path.dirname(__file__), 'static')
        if os.path.exists(work_tools_static):
            static_dirs.append(work_tools_static)
        
        # 查找Django admin静态文件
        try:
            import django
            from django.contrib import admin
            admin_static = os.path.join(os.path.dirname(admin.__file__), 'static')
            if os.path.exists(admin_static):
                static_dirs.append(admin_static)
        except ImportError:
            pass
        
        return static_dirs
    
    def _copy_static_files(self, source_dir: str, target_dir: str) -> int:
        """
        复制静态文件从源目录到目标目录
        
        Args:
            source_dir: 源目录
            target_dir: 目标目录
            
        Returns:
            int: 复制的文件数量
        """
        copied_count = 0
        
        for root, dirs, files in os.walk(source_dir):
            # 计算相对路径
            rel_path = os.path.relpath(root, source_dir)
            target_path = os.path.join(target_dir, rel_path) if rel_path != '.' else target_dir
            
            # 确保目标目录存在
            os.makedirs(target_path, exist_ok=True)
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                
                # 只复制支持的文件类型
                if file_ext in self.supported_extensions:
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_path, file)
                    
                    # 检查文件是否需要更新
                    if self._should_copy_file(source_file, target_file):
                        shutil.copy2(source_file, target_file)
                        copied_count += 1
        
        return copied_count
    
    def _should_copy_file(self, source_file: str, target_file: str) -> bool:
        """
        判断是否需要复制文件
        
        Args:
            source_file: 源文件路径
            target_file: 目标文件路径
            
        Returns:
            bool: 是否需要复制
        """
        # 如果目标文件不存在，需要复制
        if not os.path.exists(target_file):
            return True
        
        # 比较文件修改时间
        source_mtime = os.path.getmtime(source_file)
        target_mtime = os.path.getmtime(target_file)
        
        return source_mtime > target_mtime
    
    def collect_templates(self, source_dirs: Optional[List[str]] = None) -> bool:
        """
        收集模板文件
        
        Args:
            source_dirs: 源模板目录列表
            
        Returns:
            bool: 收集是否成功
        """
        try:
            dirs_to_scan = source_dirs or self._discover_template_dirs()
            collected_files = 0
            
            for source_dir in dirs_to_scan:
                if not os.path.exists(source_dir):
                    self.logger.warning(f"模板源目录不存在: {source_dir}")
                    continue
                
                files_count = self._copy_template_files(source_dir, self.templates_root)
                collected_files += files_count
                self.logger.info(f"从 {source_dir} 收集了 {files_count} 个模板文件")
            
            self.logger.info(f"模板文件收集完成，总共收集了 {collected_files} 个文件")
            return True
            
        except Exception as e:
            self.logger.error(f"收集模板文件失败: {e}")
            return False
    
    def _discover_template_dirs(self) -> List[str]:
        """自动发现模板目录"""
        template_dirs = []
        
        # 查找work_tools/templates目录
        work_tools_templates = os.path.join(os.path.dirname(__file__), 'templates')
        if os.path.exists(work_tools_templates):
            template_dirs.append(work_tools_templates)
        
        return template_dirs
    
    def _copy_template_files(self, source_dir: str, target_dir: str) -> int:
        """复制模板文件"""
        copied_count = 0
        
        for root, dirs, files in os.walk(source_dir):
            rel_path = os.path.relpath(root, source_dir)
            target_path = os.path.join(target_dir, rel_path) if rel_path != '.' else target_dir
            
            os.makedirs(target_path, exist_ok=True)
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in self.template_extensions:
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_path, file)
                    
                    if self._should_copy_file(source_file, target_file):
                        shutil.copy2(source_file, target_file)
                        copied_count += 1
        
        return copied_count
    
    def _generate_manifest(self):
        """生成静态文件清单"""
        try:
            manifest = {}
            
            for root, dirs, files in os.walk(self.static_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.static_root)
                    
                    # 计算文件哈希
                    file_hash = self._calculate_file_hash(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    manifest[rel_path] = {
                        'hash': file_hash,
                        'size': file_size,
                        'mtime': os.path.getmtime(file_path)
                    }
            
            # 保存清单文件
            manifest_path = os.path.join(self.static_root, 'manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            self.assets_manifest = manifest
            self.logger.info(f"生成静态文件清单，包含 {len(manifest)} 个文件")
            
        except Exception as e:
            self.logger.error(f"生成文件清单失败: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def verify_assets(self) -> Tuple[bool, List[str]]:
        """
        验证静态资源完整性
        
        Returns:
            Tuple[bool, List[str]]: (验证是否通过, 错误信息列表)
        """
        errors = []
        
        try:
            # 检查关键目录是否存在
            if not os.path.exists(self.static_root):
                errors.append(f"静态文件根目录不存在: {self.static_root}")
            
            if not os.path.exists(self.templates_root):
                errors.append(f"模板文件根目录不存在: {self.templates_root}")
            
            # 检查关键静态文件
            critical_files = self._get_critical_static_files()
            for file_path in critical_files:
                full_path = os.path.join(self.static_root, file_path)
                if not os.path.exists(full_path):
                    errors.append(f"关键静态文件缺失: {file_path}")
            
            # 检查模板文件
            critical_templates = self._get_critical_templates()
            for template_path in critical_templates:
                full_path = os.path.join(self.templates_root, template_path)
                if not os.path.exists(full_path):
                    errors.append(f"关键模板文件缺失: {template_path}")
            
            # 验证文件清单
            if os.path.exists(os.path.join(self.static_root, 'manifest.json')):
                manifest_errors = self._verify_manifest()
                errors.extend(manifest_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"验证过程出错: {e}")
            return False, errors
    
    def _get_critical_static_files(self) -> List[str]:
        """获取关键静态文件列表"""
        # 这里可以根据实际项目需求定义关键文件
        return [
            'admin/css/base.css',
            'admin/js/core.js'
        ]
    
    def _get_critical_templates(self) -> List[str]:
        """获取关键模板文件列表"""
        return [
            'admin/base.html',
            'admin/base_site.html'
        ]
    
    def _verify_manifest(self) -> List[str]:
        """验证文件清单"""
        errors = []
        
        try:
            manifest_path = os.path.join(self.static_root, 'manifest.json')
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            for rel_path, file_info in manifest.items():
                full_path = os.path.join(self.static_root, rel_path)
                
                if not os.path.exists(full_path):
                    errors.append(f"清单中的文件不存在: {rel_path}")
                    continue
                
                # 验证文件哈希
                current_hash = self._calculate_file_hash(full_path)
                if current_hash != file_info['hash']:
                    errors.append(f"文件哈希不匹配: {rel_path}")
                
                # 验证文件大小
                current_size = os.path.getsize(full_path)
                if current_size != file_info['size']:
                    errors.append(f"文件大小不匹配: {rel_path}")
        
        except Exception as e:
            errors.append(f"验证清单文件失败: {e}")
        
        return errors
    
    def get_static_file_url(self, file_path: str) -> str:
        """
        获取静态文件URL
        
        Args:
            file_path: 相对于静态根目录的文件路径
            
        Returns:
            str: 静态文件URL
        """
        # 在打包环境中，静态文件通过Django的静态文件服务提供
        return f"/static/{file_path.replace(os.sep, '/')}"
    
    def cleanup_old_files(self, keep_days: int = 7) -> int:
        """
        清理旧的静态文件
        
        Args:
            keep_days: 保留天数
            
        Returns:
            int: 清理的文件数量
        """
        import time
        
        cleaned_count = 0
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        
        try:
            for root, dirs, files in os.walk(self.static_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 跳过关键文件
                    rel_path = os.path.relpath(file_path, self.static_root)
                    if rel_path in self._get_critical_static_files():
                        continue
                    
                    # 检查文件修改时间
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
            
            self.logger.info(f"清理了 {cleaned_count} 个旧静态文件")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"清理旧文件失败: {e}")
            return 0
    
    def get_assets_info(self) -> Dict[str, any]:
        """获取静态资源信息"""
        info = {
            'static_root': self.static_root,
            'templates_root': self.templates_root,
            'total_files': 0,
            'total_size': 0,
            'file_types': {},
            'last_collected': None
        }
        
        try:
            # 统计静态文件
            for root, dirs, files in os.walk(self.static_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    file_size = os.path.getsize(file_path)
                    
                    info['total_files'] += 1
                    info['total_size'] += file_size
                    
                    if file_ext in info['file_types']:
                        info['file_types'][file_ext] += 1
                    else:
                        info['file_types'][file_ext] = 1
            
            # 获取最后收集时间
            manifest_path = os.path.join(self.static_root, 'manifest.json')
            if os.path.exists(manifest_path):
                info['last_collected'] = os.path.getmtime(manifest_path)
        
        except Exception as e:
            self.logger.error(f"获取资源信息失败: {e}")
        
        return info