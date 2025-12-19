"""
Path Manager for Portable EXE Packaging

This module provides the PathManager class that handles all file paths
for the portable executable, ensuring all paths are relative to the
executable location.

**Feature: portable-exe-packaging**
**Requirements: 4.1, 4.2, 4.3, 4.4, 4.5**
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union
import logging


class PathManager:
    """
    Manages all file paths for the portable application.
    
    Ensures all paths are relative to the executable location and handles
    directory creation, path calculation, and validation.
    """
    
    def __init__(self, executable_path: Optional[str] = None):
        """
        Initialize PathManager with executable path.
        
        Args:
            executable_path: Path to the executable. If None, auto-detects.
        """
        if executable_path is None:
            executable_path = self._get_executable_path()
        
        self.executable_path = Path(executable_path).resolve()
        self.base_dir = self.executable_path.parent
        
        # Initialize all standard paths
        self._initialize_paths()
        
        # Set up logging
        self.logger = logging.getLogger('app.path_manager')
    
    def _get_executable_path(self) -> str:
        """
        Auto-detect the executable path.
        
        Returns:
            Path to the current executable or script.
        """
        if getattr(sys, 'frozen', False):
            # Running as packaged executable
            return sys.executable
        else:
            # Running as script
            return os.path.abspath(sys.argv[0])
    
    def _initialize_paths(self):
        """Initialize all standard application paths."""
        # 在打包环境中，数据文件位于_internal目录
        if getattr(sys, 'frozen', False):
            # 打包环境：只读数据在_internal目录中，可写数据在可执行文件目录
            internal_dir = self.base_dir / '_internal'
            self.static_dir = internal_dir / 'static'
            self.templates_dir = internal_dir / 'templates'  
            self.db_path = internal_dir / 'db.sqlite3'
            
            # 可写目录放在可执行文件目录中
            self.logs_dir = self.base_dir / 'logs'
            self.temp_dir = self.base_dir / 'temp_files'
            self.temp_uploads_dir = self.base_dir / 'temp_uploads'
            self.config_dir = self.base_dir / 'config'
        else:
            # 开发环境：使用相对路径
            self.static_dir = self.base_dir / 'static'
            self.templates_dir = self.base_dir / 'templates'
            self.db_path = self.base_dir / 'db.sqlite3'
            self.logs_dir = self.base_dir / 'logs'
            self.temp_dir = self.base_dir / 'temp_files'
            self.temp_uploads_dir = self.base_dir / 'temp_uploads'
            self.config_dir = self.base_dir / 'config'
        
        # 这些路径在两种环境中都相同
        self.downloads_dir = self.temp_dir / 'downloads'
        self.sql_output_dir = self.temp_dir / 'sql_output'
        self.validation_failures_dir = self.temp_uploads_dir / 'validation_failures'
    
    def ensure_directories(self) -> None:
        """
        Ensure all necessary directories exist.
        
        Creates directories if they don't exist, with proper error handling.
        """
        directories = [
            self.static_dir,
            self.templates_dir,
            self.logs_dir,
            self.temp_dir,
            self.temp_uploads_dir,
            self.config_dir,
            self.downloads_dir,
            self.sql_output_dir,
            self.validation_failures_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Ensured directory exists: {directory}")
            except OSError as e:
                self.logger.error(f"Failed to create directory {directory}: {e}")
                raise
    
    def get_relative_path(self, path_type: str) -> Path:
        """
        Get relative path for a specific path type.
        
        Args:
            path_type: Type of path ('static', 'templates', 'db', 'logs', 
                      'temp', 'config', 'downloads', 'sql_output', 
                      'validation_failures')
        
        Returns:
            Path object for the requested path type.
        
        Raises:
            ValueError: If path_type is not recognized.
        """
        path_mapping = {
            'static': self.static_dir,
            'templates': self.templates_dir,
            'db': self.db_path,
            'logs': self.logs_dir,
            'temp': self.temp_dir,
            'temp_uploads': self.temp_uploads_dir,
            'config': self.config_dir,
            'downloads': self.downloads_dir,
            'sql_output': self.sql_output_dir,
            'validation_failures': self.validation_failures_dir,
            'base': self.base_dir
        }
        
        if path_type not in path_mapping:
            raise ValueError(f"Unknown path type: {path_type}. "
                           f"Available types: {list(path_mapping.keys())}")
        
        return path_mapping[path_type]
    
    def get_absolute_path(self, relative_path: Union[str, Path]) -> Path:
        """
        Convert a relative path to absolute path based on base directory.
        
        Args:
            relative_path: Path relative to the application base directory.
        
        Returns:
            Absolute path.
        """
        if isinstance(relative_path, str):
            relative_path = Path(relative_path)
        
        if relative_path.is_absolute():
            return relative_path
        
        return self.base_dir / relative_path
    
    def create_temp_file_path(self, filename: str, subdirectory: str = '') -> Path:
        """
        Create a path for a temporary file.
        
        Args:
            filename: Name of the temporary file.
            subdirectory: Optional subdirectory within temp directory.
        
        Returns:
            Path for the temporary file.
        """
        if subdirectory:
            temp_path = self.temp_dir / subdirectory
            temp_path.mkdir(parents=True, exist_ok=True)
        else:
            temp_path = self.temp_dir
        
        return temp_path / filename
    
    def create_log_file_path(self, log_name: str) -> Path:
        """
        Create a path for a log file.
        
        Args:
            log_name: Name of the log file (without extension).
        
        Returns:
            Path for the log file.
        """
        if not log_name.endswith('.log'):
            log_name += '.log'
        
        return self.logs_dir / log_name
    
    def create_download_file_path(self, filename: str) -> Path:
        """
        Create a path for a download file.
        
        Args:
            filename: Name of the download file.
        
        Returns:
            Path for the download file.
        """
        return self.downloads_dir / filename
    
    def validate_path_security(self, path: Union[str, Path]) -> bool:
        """
        Validate that a path is secure (within application directory).
        
        Args:
            path: Path to validate.
        
        Returns:
            True if path is secure, False otherwise.
        """
        try:
            if isinstance(path, str):
                path = Path(path)
            
            # Resolve the path to handle any .. or . components
            resolved_path = path.resolve()
            
            # Check if the resolved path is within the base directory
            try:
                resolved_path.relative_to(self.base_dir)
                return True
            except ValueError:
                # Path is outside base directory
                return False
        except Exception:
            return False
    
    def get_config_file_path(self, config_name: str) -> Path:
        """
        Get path for a configuration file.
        
        Args:
            config_name: Name of the configuration file.
        
        Returns:
            Path for the configuration file.
        """
        if not config_name.endswith('.json'):
            config_name += '.json'
        
        return self.config_dir / config_name
    
    def is_portable_mode(self) -> bool:
        """
        Check if running in portable mode (packaged executable).
        
        Returns:
            True if running as packaged executable, False if running as script.
        """
        return getattr(sys, 'frozen', False)
    
    def get_django_settings_paths(self) -> dict:
        """
        Get paths formatted for Django settings.
        
        Returns:
            Dictionary with paths suitable for Django settings.
        """
        return {
            'BASE_DIR': self.base_dir,
            'STATIC_ROOT': self.static_dir,
            'TEMPLATES_DIRS': [self.templates_dir],
            'DATABASE_PATH': self.db_path,
            'LOGS_DIR': self.logs_dir,
            'MEDIA_ROOT': self.temp_dir,
        }
    
    def __str__(self) -> str:
        """String representation of PathManager."""
        return f"PathManager(base_dir={self.base_dir}, portable={self.is_portable_mode()})"
    
    def __repr__(self) -> str:
        """Detailed representation of PathManager."""
        return (f"PathManager(executable_path={self.executable_path}, "
                f"base_dir={self.base_dir}, portable={self.is_portable_mode()})")