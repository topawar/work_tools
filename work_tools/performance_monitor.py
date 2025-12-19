"""
性能监控模块
负责监控应用程序的性能指标，包括启动时间、内存使用和资源统计
"""

import os
import sys
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class PerformanceMetrics:
    """性能指标数据模型"""
    startup_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    database_operations: int = 0
    database_response_time_ms: float = 0.0
    static_files_served: int = 0
    configuration_loads: int = 0
    error_count: int = 0
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'startup_time': self.startup_time,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'database_operations': self.database_operations,
            'database_response_time_ms': self.database_response_time_ms,
            'static_files_served': self.static_files_served,
            'configuration_loads': self.configuration_loads,
            'error_count': self.error_count,
            'uptime_seconds': self.uptime_seconds,
            'timestamp': self.timestamp.isoformat()
        }


class PerformanceMonitor:
    """性能监控器类"""
    
    def __init__(self, log_dir: str = None):
        """
        初始化性能监控器
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = log_dir or "logs"
        self.logger = logging.getLogger(__name__)
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
        
        # 监控状态
        self.monitoring_active = False
        self.monitor_thread = None
        self.monitor_interval = 30  # 30秒监控间隔
        
        # 历史数据
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 100
        
        # 性能阈值
        self.thresholds = {
            'startup_time_max': 15.0,  # 最大启动时间（秒）
            'memory_usage_max': 500.0,  # 最大内存使用（MB）
            'database_response_max': 1000.0,  # 最大数据库响应时间（毫秒）
            'error_rate_max': 0.05  # 最大错误率（5%）
        }
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
    
    def start_monitoring(self):
        """开始性能监控"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("性能监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._check_thresholds()
                self._save_metrics()
                time.sleep(self.monitor_interval)
            except Exception as e:
                self.logger.error(f"性能监控循环出错: {e}")
                time.sleep(self.monitor_interval)
    
    def _collect_metrics(self):
        """收集性能指标"""
        try:
            # 更新运行时间
            self.metrics.uptime_seconds = time.time() - self.start_time
            
            # 收集内存使用情况
            self.metrics.memory_usage_mb = self._get_memory_usage()
            
            # 收集CPU使用情况（简化版本）
            self.metrics.cpu_usage_percent = self._get_cpu_usage()
            
            # 更新时间戳
            self.metrics.timestamp = datetime.now()
            
            # 添加到历史记录
            self._add_to_history()
            
        except Exception as e:
            self.logger.error(f"收集性能指标失败: {e}")
    
    def _get_memory_usage(self) -> float:
        """获取内存使用情况（MB）"""
        try:
            # 尝试使用psutil（如果可用）
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                return memory_info.rss / 1024 / 1024  # 转换为MB
            except ImportError:
                pass
            
            # 备用方法：使用系统信息
            if sys.platform == "win32":
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # 获取进程句柄
                    kernel32 = ctypes.windll.kernel32
                    process_handle = kernel32.GetCurrentProcess()
                    
                    # 获取内存信息
                    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                        _fields_ = [
                            ("cb", wintypes.DWORD),
                            ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t),
                        ]
                    
                    counters = PROCESS_MEMORY_COUNTERS()
                    counters.cb = ctypes.sizeof(counters)
                    
                    if kernel32.GetProcessMemoryInfo(process_handle, ctypes.byref(counters), counters.cb):
                        return counters.WorkingSetSize / 1024 / 1024  # 转换为MB
                except Exception:
                    pass
            
            # 如果都失败，返回估算值
            return 50.0  # 默认估算值
            
        except Exception as e:
            self.logger.warning(f"获取内存使用情况失败: {e}")
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """获取CPU使用情况（简化版本）"""
        try:
            # 这是一个简化的CPU使用率估算
            # 在实际应用中，可以使用psutil或其他工具获取更准确的数据
            return 0.0  # 暂时返回0，避免复杂的CPU监控
        except Exception as e:
            self.logger.warning(f"获取CPU使用情况失败: {e}")
            return 0.0
    
    def _add_to_history(self):
        """添加指标到历史记录"""
        # 创建当前指标的副本
        current_metrics = PerformanceMetrics(
            startup_time=self.metrics.startup_time,
            memory_usage_mb=self.metrics.memory_usage_mb,
            cpu_usage_percent=self.metrics.cpu_usage_percent,
            database_operations=self.metrics.database_operations,
            database_response_time_ms=self.metrics.database_response_time_ms,
            static_files_served=self.metrics.static_files_served,
            configuration_loads=self.metrics.configuration_loads,
            error_count=self.metrics.error_count,
            uptime_seconds=self.metrics.uptime_seconds,
            timestamp=self.metrics.timestamp
        )
        
        self.metrics_history.append(current_metrics)
        
        # 限制历史记录大小
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
    
    def _check_thresholds(self):
        """检查性能阈值"""
        try:
            # 检查启动时间
            if self.metrics.startup_time > self.thresholds['startup_time_max']:
                self.logger.warning(f"启动时间超过阈值: {self.metrics.startup_time:.2f}s")
            
            # 检查内存使用
            if self.metrics.memory_usage_mb > self.thresholds['memory_usage_max']:
                self.logger.warning(f"内存使用超过阈值: {self.metrics.memory_usage_mb:.2f}MB")
            
            # 检查数据库响应时间
            if self.metrics.database_response_time_ms > self.thresholds['database_response_max']:
                self.logger.warning(f"数据库响应时间超过阈值: {self.metrics.database_response_time_ms:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"检查性能阈值失败: {e}")
    
    def _save_metrics(self):
        """保存性能指标到文件"""
        try:
            metrics_file = os.path.join(self.log_dir, "performance_metrics.json")
            
            # 准备要保存的数据
            data = {
                'current_metrics': self.metrics.to_dict(),
                'history': [m.to_dict() for m in self.metrics_history[-10:]],  # 只保存最近10条
                'thresholds': self.thresholds,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"保存性能指标失败: {e}")
    
    def record_startup_time(self, startup_time: float):
        """记录启动时间"""
        self.metrics.startup_time = startup_time
        self.logger.info(f"启动时间: {startup_time:.2f}秒")
    
    def record_database_operation(self, response_time_ms: float):
        """记录数据库操作"""
        self.metrics.database_operations += 1
        
        # 更新平均响应时间
        if self.metrics.database_operations == 1:
            self.metrics.database_response_time_ms = response_time_ms
        else:
            # 计算移动平均
            self.metrics.database_response_time_ms = (
                (self.metrics.database_response_time_ms * (self.metrics.database_operations - 1) + response_time_ms) /
                self.metrics.database_operations
            )
    
    def record_static_file_served(self):
        """记录静态文件服务"""
        self.metrics.static_files_served += 1
    
    def record_configuration_load(self):
        """记录配置加载"""
        self.metrics.configuration_loads += 1
    
    def record_error(self):
        """记录错误"""
        self.metrics.error_count += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        return self.metrics
    
    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """获取性能指标历史"""
        return self.metrics_history.copy()
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        try:
            if not self.metrics_history:
                return {
                    'status': 'no_data',
                    'message': '暂无性能数据'
                }
            
            # 计算统计信息
            recent_metrics = self.metrics_history[-10:]  # 最近10条记录
            
            avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
            max_memory = max(m.memory_usage_mb for m in recent_metrics)
            
            avg_db_response = sum(m.database_response_time_ms for m in recent_metrics) / len(recent_metrics)
            max_db_response = max(m.database_response_time_ms for m in recent_metrics)
            
            total_operations = sum(m.database_operations for m in recent_metrics)
            total_errors = sum(m.error_count for m in recent_metrics)
            
            error_rate = (total_errors / max(total_operations, 1)) if total_operations > 0 else 0
            
            # 性能评级
            performance_score = self._calculate_performance_score()
            
            return {
                'status': 'ok',
                'uptime_hours': self.metrics.uptime_seconds / 3600,
                'startup_time': self.metrics.startup_time,
                'memory_usage': {
                    'current_mb': self.metrics.memory_usage_mb,
                    'average_mb': avg_memory,
                    'peak_mb': max_memory
                },
                'database_performance': {
                    'total_operations': self.metrics.database_operations,
                    'average_response_ms': avg_db_response,
                    'peak_response_ms': max_db_response
                },
                'error_statistics': {
                    'total_errors': self.metrics.error_count,
                    'error_rate': error_rate
                },
                'performance_score': performance_score,
                'recommendations': self._get_performance_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"获取性能摘要失败: {e}")
            return {
                'status': 'error',
                'message': f'获取性能摘要失败: {e}'
            }
    
    def _calculate_performance_score(self) -> float:
        """计算性能评分（0-100）"""
        try:
            score = 100.0
            
            # 启动时间评分（权重20%）
            if self.metrics.startup_time > 0:
                startup_penalty = min(self.metrics.startup_time / self.thresholds['startup_time_max'], 1.0) * 20
                score -= startup_penalty
            
            # 内存使用评分（权重30%）
            if self.metrics.memory_usage_mb > 0:
                memory_penalty = min(self.metrics.memory_usage_mb / self.thresholds['memory_usage_max'], 1.0) * 30
                score -= memory_penalty
            
            # 数据库响应时间评分（权重30%）
            if self.metrics.database_response_time_ms > 0:
                db_penalty = min(self.metrics.database_response_time_ms / self.thresholds['database_response_max'], 1.0) * 30
                score -= db_penalty
            
            # 错误率评分（权重20%）
            if self.metrics.database_operations > 0:
                error_rate = self.metrics.error_count / self.metrics.database_operations
                error_penalty = min(error_rate / self.thresholds['error_rate_max'], 1.0) * 20
                score -= error_penalty
            
            return max(score, 0.0)
            
        except Exception as e:
            self.logger.error(f"计算性能评分失败: {e}")
            return 50.0  # 默认中等评分
    
    def _get_performance_recommendations(self) -> List[str]:
        """获取性能优化建议"""
        recommendations = []
        
        try:
            # 启动时间建议
            if self.metrics.startup_time > self.thresholds['startup_time_max']:
                recommendations.append("启动时间较长，建议优化应用初始化流程")
            
            # 内存使用建议
            if self.metrics.memory_usage_mb > self.thresholds['memory_usage_max']:
                recommendations.append("内存使用较高，建议检查内存泄漏或优化数据结构")
            
            # 数据库性能建议
            if self.metrics.database_response_time_ms > self.thresholds['database_response_max']:
                recommendations.append("数据库响应较慢，建议优化查询或添加索引")
            
            # 错误率建议
            if self.metrics.database_operations > 0:
                error_rate = self.metrics.error_count / self.metrics.database_operations
                if error_rate > self.thresholds['error_rate_max']:
                    recommendations.append("错误率较高，建议检查错误处理和数据验证")
            
            # 通用建议
            if self.metrics.uptime_seconds > 24 * 3600:  # 运行超过24小时
                recommendations.append("应用已长时间运行，建议定期重启以释放资源")
            
            if not recommendations:
                recommendations.append("性能表现良好，继续保持")
            
        except Exception as e:
            self.logger.error(f"生成性能建议失败: {e}")
            recommendations.append("无法生成性能建议，请检查监控系统")
        
        return recommendations
    
    def export_metrics(self, file_path: str) -> bool:
        """导出性能指标到文件"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'current_metrics': self.metrics.to_dict(),
                'metrics_history': [m.to_dict() for m in self.metrics_history],
                'performance_summary': self.get_performance_summary(),
                'thresholds': self.thresholds
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"性能指标已导出到: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出性能指标失败: {e}")
            return False
    
    def reset_metrics(self):
        """重置性能指标"""
        self.metrics = PerformanceMetrics()
        self.metrics_history.clear()
        self.start_time = time.time()
        self.logger.info("性能指标已重置")


# 全局性能监控器实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def initialize_performance_monitoring(log_dir: str = None):
    """初始化性能监控"""
    global _global_monitor
    _global_monitor = PerformanceMonitor(log_dir)
    _global_monitor.start_monitoring()
    return _global_monitor