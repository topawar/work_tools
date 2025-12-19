"""
错误处理系统模块
提供各种错误场景的处理机制，包括启动错误、数据库错误、文件系统错误等
"""

import os
import sys
import time
import shutil
import logging
import traceback
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    code: str
    message: str
    severity: ErrorSeverity
    details: Optional[str] = None
    suggestions: Optional[List[str]] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BaseErrorHandler:
    """错误处理器基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(f'app.error.{self.__class__.__name__}')
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理错误的主方法"""
        raise NotImplementedError
    
    def log_error(self, error_info: ErrorInfo, context: Dict[str, Any] = None):
        """记录错误日志"""
        log_message = f"[{error_info.code}] {error_info.message}"
        if error_info.details:
            log_message += f" - {error_info.details}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        if context:
            self.logger.debug(f"错误上下文: {context}")


class StartupErrorHandler(BaseErrorHandler):
    """启动错误处理器"""
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理启动相关错误"""
        context = context or {}
        
        if isinstance(error, ImportError):
            return self._handle_import_error(error, context)
        elif isinstance(error, PermissionError):
            return self._handle_permission_error(error, context)
        elif isinstance(error, FileNotFoundError):
            return self._handle_file_not_found_error(error, context)
        elif "port" in str(error).lower() or "address" in str(error).lower():
            return self._handle_port_error(error, context)
        else:
            return self._handle_generic_startup_error(error, context)
    
    def _handle_import_error(self, error: ImportError, context: Dict[str, Any]) -> ErrorInfo:
        """处理导入错误"""
        missing_module = str(error).replace("No module named ", "").strip("'\"")
        
        return ErrorInfo(
            code="STARTUP_IMPORT_ERROR",
            message=f"缺少必要的Python模块: {missing_module}",
            severity=ErrorSeverity.CRITICAL,
            details=str(error),
            suggestions=[
                f"请安装缺少的模块: pip install {missing_module}",
                "检查Python环境是否正确配置",
                "如果是打包环境，请检查模块是否正确打包"
            ]
        )
    
    def _handle_permission_error(self, error: PermissionError, context: Dict[str, Any]) -> ErrorInfo:
        """处理权限错误"""
        file_path = context.get('file_path', '未知文件')
        
        return ErrorInfo(
            code="STARTUP_PERMISSION_ERROR",
            message=f"文件权限不足: {file_path}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "以管理员身份运行应用程序",
                "检查文件和目录的读写权限",
                "确保应用程序目录不在受保护的系统目录中"
            ]
        )
    
    def _handle_file_not_found_error(self, error: FileNotFoundError, context: Dict[str, Any]) -> ErrorInfo:
        """处理文件未找到错误"""
        file_path = context.get('file_path', str(error).split("'")[1] if "'" in str(error) else '未知文件')
        
        return ErrorInfo(
            code="STARTUP_FILE_NOT_FOUND",
            message=f"找不到必要的文件: {file_path}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查文件是否存在于正确的位置",
                "重新安装或重新部署应用程序",
                "检查文件路径配置是否正确"
            ]
        )
    
    def _handle_port_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """处理端口相关错误"""
        port = context.get('port', '未知端口')
        
        return ErrorInfo(
            code="STARTUP_PORT_ERROR",
            message=f"端口 {port} 不可用或被占用",
            severity=ErrorSeverity.WARNING,
            details=str(error),
            suggestions=[
                f"尝试使用其他端口",
                f"检查端口 {port} 是否被其他程序占用",
                "重启计算机以释放被占用的端口",
                "在配置中指定不同的端口号"
            ]
        )
    
    def _handle_generic_startup_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """处理通用启动错误"""
        return ErrorInfo(
            code="STARTUP_GENERIC_ERROR",
            message=f"应用程序启动失败: {type(error).__name__}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查系统环境和依赖",
                "查看详细日志获取更多信息",
                "尝试重新启动应用程序",
                "联系技术支持"
            ]
        )
    
    def handle_port_conflict(self, port: int) -> int:
        """处理端口冲突，返回可用端口"""
        for new_port in range(port + 1, port + 100):
            if self._is_port_available(new_port):
                self.logger.info(f"端口 {port} 被占用，使用端口 {new_port}")
                return new_port
        
        # 如果找不到可用端口，返回原端口并记录错误
        self.logger.error(f"无法找到 {port} 附近的可用端口")
        return port
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result != 0
        except Exception:
            return False


class DatabaseErrorHandler(BaseErrorHandler):
    """数据库错误处理器"""
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理数据库相关错误"""
        context = context or {}
        
        if isinstance(error, sqlite3.DatabaseError):
            return self._handle_sqlite_error(error, context)
        elif isinstance(error, sqlite3.OperationalError):
            return self._handle_operational_error(error, context)
        elif isinstance(error, sqlite3.IntegrityError):
            return self._handle_integrity_error(error, context)
        else:
            return self._handle_generic_database_error(error, context)
    
    def _handle_sqlite_error(self, error: sqlite3.DatabaseError, context: Dict[str, Any]) -> ErrorInfo:
        """处理SQLite数据库错误"""
        db_path = context.get('db_path', '未知数据库')
        
        return ErrorInfo(
            code="DATABASE_SQLITE_ERROR",
            message=f"SQLite数据库错误: {db_path}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查数据库文件是否损坏",
                "尝试从备份恢复数据库",
                "检查磁盘空间是否充足",
                "重新创建数据库"
            ]
        )
    
    def _handle_operational_error(self, error: sqlite3.OperationalError, context: Dict[str, Any]) -> ErrorInfo:
        """处理操作错误"""
        if "locked" in str(error).lower():
            return ErrorInfo(
                code="DATABASE_LOCKED_ERROR",
                message="数据库被锁定，无法访问",
                severity=ErrorSeverity.WARNING,
                details=str(error),
                suggestions=[
                    "等待其他操作完成后重试",
                    "检查是否有其他程序正在使用数据库",
                    "重启应用程序",
                    "检查数据库文件权限"
                ]
            )
        else:
            return ErrorInfo(
                code="DATABASE_OPERATIONAL_ERROR",
                message="数据库操作错误",
                severity=ErrorSeverity.ERROR,
                details=str(error),
                suggestions=[
                    "检查SQL语句语法",
                    "验证表结构是否正确",
                    "检查数据库连接状态"
                ]
            )
    
    def _handle_integrity_error(self, error: sqlite3.IntegrityError, context: Dict[str, Any]) -> ErrorInfo:
        """处理完整性错误"""
        return ErrorInfo(
            code="DATABASE_INTEGRITY_ERROR",
            message="数据库完整性约束违反",
            severity=ErrorSeverity.WARNING,
            details=str(error),
            suggestions=[
                "检查数据是否符合约束条件",
                "验证外键关系",
                "检查唯一性约束",
                "修正数据后重试"
            ]
        )
    
    def _handle_generic_database_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """处理通用数据库错误"""
        return ErrorInfo(
            code="DATABASE_GENERIC_ERROR",
            message=f"数据库错误: {type(error).__name__}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查数据库连接",
                "验证数据库文件完整性",
                "查看详细日志",
                "联系技术支持"
            ]
        )
    
    def handle_database_corruption(self, db_path: str) -> bool:
        """处理数据库损坏"""
        try:
            backup_path = f"{db_path}.backup"
            
            # 检查是否有备份文件
            if os.path.exists(backup_path):
                self.logger.info(f"发现备份文件，尝试恢复: {backup_path}")
                shutil.copy2(backup_path, db_path)
                return True
            
            # 尝试修复数据库
            self.logger.info("尝试修复损坏的数据库")
            return self._attempt_database_repair(db_path)
            
        except Exception as e:
            self.logger.error(f"数据库恢复失败: {e}")
            return False
    
    def _attempt_database_repair(self, db_path: str) -> bool:
        """尝试修复数据库"""
        try:
            # 创建临时数据库
            temp_db_path = f"{db_path}.temp"
            
            # 尝试导出数据
            conn = sqlite3.connect(db_path)
            temp_conn = sqlite3.connect(temp_db_path)
            
            # 执行数据库完整性检查和修复
            conn.execute("PRAGMA integrity_check")
            conn.backup(temp_conn)
            
            conn.close()
            temp_conn.close()
            
            # 替换原数据库
            shutil.move(temp_db_path, db_path)
            
            self.logger.info("数据库修复成功")
            return True
            
        except Exception as e:
            self.logger.error(f"数据库修复失败: {e}")
            # 清理临时文件
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
            return False


class FileSystemErrorHandler(BaseErrorHandler):
    """文件系统错误处理器"""
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理文件系统相关错误"""
        context = context or {}
        
        if isinstance(error, PermissionError):
            return self._handle_permission_error(error, context)
        elif isinstance(error, FileNotFoundError):
            return self._handle_file_not_found_error(error, context)
        elif isinstance(error, OSError) and "No space left" in str(error):
            return self._handle_disk_space_error(error, context)
        elif isinstance(error, OSError):
            return self._handle_os_error(error, context)
        else:
            return self._handle_generic_filesystem_error(error, context)
    
    def _handle_permission_error(self, error: PermissionError, context: Dict[str, Any]) -> ErrorInfo:
        """处理权限错误"""
        file_path = context.get('file_path', '未知文件')
        
        return ErrorInfo(
            code="FILESYSTEM_PERMISSION_ERROR",
            message=f"文件权限不足: {file_path}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查文件和目录权限",
                "以管理员身份运行",
                "确保文件未被其他程序占用",
                "检查文件是否为只读"
            ]
        )
    
    def _handle_file_not_found_error(self, error: FileNotFoundError, context: Dict[str, Any]) -> ErrorInfo:
        """处理文件未找到错误"""
        file_path = context.get('file_path', '未知文件')
        
        return ErrorInfo(
            code="FILESYSTEM_FILE_NOT_FOUND",
            message=f"文件不存在: {file_path}",
            severity=ErrorSeverity.WARNING,
            details=str(error),
            suggestions=[
                "检查文件路径是否正确",
                "确认文件是否已被删除或移动",
                "重新创建缺失的文件",
                "检查路径配置"
            ]
        )
    
    def _handle_disk_space_error(self, error: OSError, context: Dict[str, Any]) -> ErrorInfo:
        """处理磁盘空间不足错误"""
        return ErrorInfo(
            code="FILESYSTEM_DISK_SPACE_ERROR",
            message="磁盘空间不足",
            severity=ErrorSeverity.CRITICAL,
            details=str(error),
            suggestions=[
                "清理磁盘空间",
                "删除不必要的文件",
                "移动应用程序到其他磁盘",
                "检查临时文件目录"
            ]
        )
    
    def _handle_os_error(self, error: OSError, context: Dict[str, Any]) -> ErrorInfo:
        """处理操作系统错误"""
        return ErrorInfo(
            code="FILESYSTEM_OS_ERROR",
            message=f"操作系统错误: {error.errno}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查系统资源",
                "重启应用程序",
                "检查文件系统状态",
                "联系系统管理员"
            ]
        )
    
    def _handle_generic_filesystem_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """处理通用文件系统错误"""
        return ErrorInfo(
            code="FILESYSTEM_GENERIC_ERROR",
            message=f"文件系统错误: {type(error).__name__}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "检查文件系统状态",
                "重试操作",
                "检查文件路径",
                "查看系统日志"
            ]
        )
    
    def check_disk_space(self, path: str, required_space: int) -> Tuple[bool, int]:
        """检查磁盘空间"""
        try:
            free_space = shutil.disk_usage(path).free
            return free_space >= required_space, free_space
        except Exception as e:
            self.logger.error(f"检查磁盘空间失败: {e}")
            return False, 0
    
    def validate_path(self, path: str) -> bool:
        """验证路径有效性"""
        try:
            normalized_path = os.path.normpath(path)
            # 检查路径是否包含非法字符
            illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
            return not any(char in normalized_path for char in illegal_chars)
        except Exception:
            return False


class ErrorManager:
    """错误管理器 - 统一错误处理入口"""
    
    def __init__(self):
        self.handlers = {
            'startup': StartupErrorHandler(),
            'database': DatabaseErrorHandler(),
            'filesystem': FileSystemErrorHandler()
        }
        self.logger = logging.getLogger('app.error.manager')
        self.error_history = []
    
    def handle_error(self, error: Exception, error_type: str = 'generic', 
                    context: Dict[str, Any] = None) -> ErrorInfo:
        """统一错误处理入口"""
        try:
            # 获取对应的错误处理器
            handler = self.handlers.get(error_type)
            
            if handler:
                error_info = handler.handle_error(error, context)
            else:
                error_info = self._handle_generic_error(error, context)
            
            # 记录错误
            self._record_error(error_info, error_type, context)
            
            # 记录日志
            if handler:
                handler.log_error(error_info, context)
            else:
                self.logger.error(f"未处理的错误: {error}")
            
            return error_info
            
        except Exception as e:
            # 错误处理器本身出错
            self.logger.critical(f"错误处理器失败: {e}")
            return ErrorInfo(
                code="ERROR_HANDLER_FAILURE",
                message="错误处理系统故障",
                severity=ErrorSeverity.CRITICAL,
                details=str(e)
            )
    
    def _handle_generic_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理通用错误"""
        return ErrorInfo(
            code="GENERIC_ERROR",
            message=f"未分类错误: {type(error).__name__}",
            severity=ErrorSeverity.ERROR,
            details=str(error),
            suggestions=[
                "查看详细日志获取更多信息",
                "尝试重新执行操作",
                "重启应用程序",
                "联系技术支持"
            ]
        )
    
    def _record_error(self, error_info: ErrorInfo, error_type: str, context: Dict[str, Any] = None):
        """记录错误到历史记录"""
        error_record = {
            'error_info': error_info,
            'error_type': error_type,
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        self.error_history.append(error_record)
        
        # 保持历史记录在合理范围内
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-50:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.error_history:
            return {'total_errors': 0}
        
        stats = {
            'total_errors': len(self.error_history),
            'by_severity': {},
            'by_type': {},
            'by_code': {},
            'recent_errors': []
        }
        
        for record in self.error_history:
            error_info = record['error_info']
            error_type = record['error_type']
            
            # 按严重程度统计
            severity = error_info.severity.value
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # 按类型统计
            stats['by_type'][error_type] = stats['by_type'].get(error_type, 0) + 1
            
            # 按错误代码统计
            code = error_info.code
            stats['by_code'][code] = stats['by_code'].get(code, 0) + 1
        
        # 最近的错误
        stats['recent_errors'] = [
            {
                'code': record['error_info'].code,
                'message': record['error_info'].message,
                'severity': record['error_info'].severity.value,
                'timestamp': record['error_info'].timestamp,
                'type': record['error_type']
            }
            for record in self.error_history[-10:]
        ]
        
        return stats
    
    def display_user_friendly_error(self, error_info: ErrorInfo) -> str:
        """生成用户友好的错误信息"""
        message_parts = [
            f"❌ {error_info.message}",
            ""
        ]
        
        if error_info.details and error_info.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            message_parts.extend([
                "详细信息:",
                f"  {error_info.details}",
                ""
            ])
        
        if error_info.suggestions:
            message_parts.extend([
                "建议解决方案:",
                *[f"  • {suggestion}" for suggestion in error_info.suggestions],
                ""
            ])
        
        message_parts.extend([
            f"错误代码: {error_info.code}",
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error_info.timestamp))}"
        ])
        
        return "\n".join(message_parts)


# 全局错误管理器实例
error_manager = ErrorManager()