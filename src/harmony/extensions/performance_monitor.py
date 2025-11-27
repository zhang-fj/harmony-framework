"""
性能监控和指标收集系统 - 提供全面的框架性能监控
"""

import functools
import gc
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    TIMER = "timer"
    HISTOGRAM = "histogram"
    METER = "meter"


@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: Union[int, float, Dict]
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0
    gc_stats: Dict[str, int] = field(default_factory=dict)
    thread_count: int = 0
    open_files: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


class MetricRegistry:
    """指标注册表"""

    def __init__(self, max_history: int = 1000):
        self._metrics: Dict[str, MetricValue] = {}
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.RLock()
        self._max_history = max_history

    def register_counter(self, name: str, description: str = "", tags: Dict[str, str] = None) -> 'Counter':
        """注册计数器"""
        with self._lock:
            metric = Counter(name, description, tags or {})
            self._metrics[name] = MetricValue(name, 0, MetricType.COUNTER, tags=tags or {}, description=description)
            return metric

    def register_gauge(self, name: str, description: str = "", tags: Dict[str, str] = None) -> 'Gauge':
        """注册仪表"""
        with self._lock:
            metric = Gauge(name, description, tags or {})
            self._metrics[name] = MetricValue(name, 0, MetricType.GAUGE, tags=tags or {}, description=description)
            return metric

    def register_timer(self, name: str, description: str = "", tags: Dict[str, str] = None) -> 'Timer':
        """注册计时器"""
        with self._lock:
            metric = Timer(name, description, tags or {})
            self._metrics[name] = MetricValue(name, {}, MetricType.TIMER, tags=tags or {}, description=description)
            return metric

    def register_histogram(self, name: str, buckets: List[float] = None, description: str = "",
                           tags: Dict[str, str] = None) -> 'Histogram':
        """注册直方图"""
        with self._lock:
            metric = Histogram(name, buckets or [], description, tags or {})
            self._metrics[name] = MetricValue(name, {}, MetricType.HISTOGRAM, tags=tags or {}, description=description)
            return metric

    def register_meter(self, name: str, description: str = "", tags: Dict[str, str] = None) -> 'Meter':
        """注册计量器"""
        with self._lock:
            metric = Meter(name, description, tags or {})
            self._metrics[name] = MetricValue(name, {}, MetricType.METER, tags=tags or {}, description=description)
            return metric

    def update_metric(self, name: str, value: Any):
        """更新指标值"""
        with self._lock:
            if name in self._metrics:
                self._metrics[name].value = value
                self._metrics[name].timestamp = time.time()
                self._history[name].append(self._metrics[name]._asdict())

    def get_metric(self, name: str) -> Optional[MetricValue]:
        """获取指标值"""
        with self._lock:
            return self._metrics.get(name)

    def get_all_metrics(self) -> Dict[str, MetricValue]:
        """获取所有指标"""
        with self._lock:
            return self._metrics.copy()

    def get_metric_history(self, name: str) -> List[Dict]:
        """获取指标历史"""
        with self._lock:
            return list(self._history[name])

    def clear_metrics(self):
        """清空所有指标"""
        with self._lock:
            self._metrics.clear()
            self._history.clear()


class Counter:
    """计数器指标"""

    def __init__(self, name: str, description: str = "", tags: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, amount: int = 1):
        """递增计数"""
        with self._lock:
            self._value += amount

    def decrement(self, amount: int = 1):
        """递减计数"""
        with self._lock:
            self._value -= amount

    def get_value(self) -> int:
        """获取当前值"""
        return self._value


class Gauge:
    """仪表指标"""

    def __init__(self, name: str, description: str = "", tags: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._value = 0
        self._lock = threading.Lock()

    def set_value(self, value: float):
        """设置值"""
        with self._lock:
            self._value = value

    def increment(self, amount: float = 1.0):
        """递增"""
        with self._lock:
            self._value += amount

    def decrement(self, amount: float = 1.0):
        """递减"""
        with self._lock:
            self._value -= amount

    def get_value(self) -> float:
        """获取当前值"""
        return self._value


class Timer:
    """计时器指标"""

    def __init__(self, name: str, description: str = "", tags: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._times: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def record(self, duration: float):
        """记录时间"""
        with self._lock:
            self._times.append(duration)

    def time_function(self, func):
        """函数装饰器，自动计时"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                self.record(duration)

        return wrapper

    def time_context(self):
        """上下文管理器，自动计时"""
        return TimerContext(self)

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        with self._lock:
            if not self._times:
                return {
                    'count': 0,
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'sum': 0.0
                }

            times_list = list(self._times)
            return {
                'count': len(times_list),
                'mean': sum(times_list) / len(times_list),
                'min': min(times_list),
                'max': max(times_list),
                'sum': sum(times_list),
                'p50': self._percentile(times_list, 0.5),
                'p95': self._percentile(times_list, 0.95),
                'p99': self._percentile(times_list, 0.99)
            }

    def _percentile(self, times: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not times:
            return 0.0
        sorted_times = sorted(times)
        index = int(len(sorted_times) * percentile)
        return sorted_times[min(index, len(sorted_times) - 1)]


class TimerContext:
    """计时器上下文管理器"""

    def __init__(self, timer: Timer):
        self.timer = timer
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.timer.record(duration)


class Histogram:
    """直方图指标"""

    def __init__(self, name: str, buckets: List[float] = None, description: str = "", tags: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self.buckets = buckets or [1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._overflow_count = 0
        self._underflow_count = 0
        self._count = 0
        self._sum = 0.0
        self._lock = threading.Lock()

    def observe(self, value: float):
        """观察值"""
        with self._lock:
            self._count += 1
            self._sum += value

            # 找到合适的桶
            bucket_found = False
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
                    bucket_found = True
                    break

            if not bucket_found:
                self._overflow_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'count': self._count,
                'sum': self._sum,
                'mean': self._sum / self._count if self._count > 0 else 0.0,
                'bucket_counts': self._bucket_counts.copy(),
                'underflow_count': self._underflow_count,
                'overflow_count': self._overflow_count,
                'buckets': self.buckets
            }


class Meter:
    """计量器指标 - 测量事件发生的速率"""

    def __init__(self, name: str, description: str = "", tags: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._count = 0
        self._rate = 0.0
        self._last_update = time.time()
        self._lock = threading.Lock()

    def mark(self, count: int = 1):
        """标记事件发生"""
        with self._lock:
            self._count += count
            current_time = time.time()
            time_diff = current_time - self._last_update

            if time_diff > 0:
                self._rate = count / time_diff
                self._last_update = current_time

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        with self._lock:
            current_time = time.time()
            time_diff = current_time - self._last_update

            if time_diff > 0:
                # 如果距离上次更新有间隔，重新计算速率
                self._rate = max(0, self._rate * (1 - time_diff))

            return {
                'count': self._count,
                'rate': self._rate
            }


class PerformanceCollector:
    """性能数据收集器"""

    def __init__(self, collection_interval: float = 10.0):
        self.collection_interval = collection_interval
        self._snapshots: deque = deque(maxlen=100)
        self._collecting = False
        self._collect_thread = None
        self._lock = threading.RLock()

    def start_collecting(self):
        """开始收集性能数据"""
        if self._collecting:
            return

        self._collecting = True
        self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collect_thread.start()

    def stop_collecting(self):
        """停止收集性能数据"""
        self._collecting = False
        if self._collect_thread:
            self._collect_thread.join(timeout=5.0)

    def _collect_loop(self):
        """收集循环"""
        while self._collecting:
            try:
                snapshot = self._collect_system_snapshot()
                with self._lock:
                    self._snapshots.append(snapshot)
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Performance collection error: {e}")

    def _collect_system_snapshot(self) -> PerformanceSnapshot:
        """收集系统快照"""
        try:
            # CPU使用率
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent()

                # 内存使用情况
                memory = psutil.virtual_memory()
                memory_usage_mb = memory.used / 1024 / 1024
                memory_percent = memory.percent

                # 打开文件数
                try:
                    open_files = len(psutil.Process().open_files())
                except:
                    open_files = 0
            else:
                # 如果没有psutil，使用基本指标
                cpu_percent = 0.0
                memory_usage_mb = 0.0
                memory_percent = 0.0
                open_files = 0

            # GC统计（总是可用）
            gc_stats = gc.get_stats() if hasattr(gc, 'get_stats') else {}

            # 线程数
            thread_count = threading.active_count()

            return PerformanceSnapshot(
                cpu_percent=cpu_percent,
                memory_usage_mb=memory_usage_mb,
                memory_percent=memory_percent,
                gc_stats=gc_stats,
                thread_count=thread_count,
                open_files=open_files
            )
        except Exception as e:
            print(f"Error collecting system snapshot: {e}")
            return PerformanceSnapshot()

    def add_custom_metric(self, name: str, value: Any):
        """添加自定义指标到最新快照"""
        with self._lock:
            if self._snapshots:
                self._snapshots[-1].custom_metrics[name] = value

    def get_latest_snapshot(self) -> Optional[PerformanceSnapshot]:
        """获取最新快照"""
        with self._lock:
            if self._snapshots:
                return self._snapshots[-1]
        return None

    def get_snapshots(self, count: int = None) -> List[PerformanceSnapshot]:
        """获取快照历史"""
        with self._lock:
            snapshots = list(self._snapshots)
            if count:
                return snapshots[-count:]
            return snapshots

    def get_average_metrics(self, duration_minutes: int = 5) -> Dict[str, float]:
        """获取平均指标"""
        end_time = time.time()
        start_time = end_time - (duration_minutes * 60)

        with self._lock:
            relevant_snapshots = [
                s for s in self._snapshots
                if start_time <= s.timestamp <= end_time
            ]

        if not relevant_snapshots:
            return {}

        avg_cpu = sum(s.cpu_percent for s in relevant_snapshots) / len(relevant_snapshots)
        avg_memory = sum(s.memory_usage_mb for s in relevant_snapshots) / len(relevant_snapshots)

        return {
            'cpu_percent': avg_cpu,
            'memory_usage_mb': avg_memory,
            'snapshot_count': len(relevant_snapshots)
        }

    def export_metrics(self, file_path: str, format: str = 'json'):
        """导出指标到文件"""
        with self._lock:
            data = {
                'snapshots': [snapshot.__dict__ for snapshot in self._snapshots],
                'collection_interval': self.collection_interval,
                'export_time': time.time()
            }

        if format.lower() == 'json':
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, collection_interval: float = 10.0):
        self.registry = MetricRegistry()
        self.collector = PerformanceCollector(collection_interval)
        self._enabled = False
        self._custom_collectors: List[Callable[[], Dict[str, Any]]] = []

    def enable(self):
        """启用性能监控"""
        if not self._enabled:
            self._enabled = True
            self.collector.start_collecting()

    def disable(self):
        """禁用性能监控"""
        if self._enabled:
            self._enabled = False
            self.collector.stop_collecting()

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

    def register_custom_collector(self, collector: Callable[[], Dict[str, Any]]):
        """注册自定义收集器"""
        self._custom_collectors.append(collector)

    def collect_custom_metrics(self):
        """收集自定义指标"""
        for collector in self._custom_collectors:
            try:
                metrics = collector()
                for name, value in metrics.items():
                    self.collector.add_custom_metric(name, value)
            except Exception as e:
                print(f"Custom collector error: {e}")

    def get_registry(self) -> MetricRegistry:
        """获取指标注册表"""
        return self.registry

    def get_collector(self) -> PerformanceCollector:
        """获取性能收集器"""
        return self.collector

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """获取综合性能报告"""
        if not self._enabled:
            return {'status': 'disabled'}

        latest_snapshot = self.collector.get_latest_snapshot()
        metrics = self.registry.get_all_metrics()
        recent_metrics = self.collector.get_average_metrics(duration_minutes=5)

        report = {
            'status': 'enabled',
            'timestamp': time.time(),
            'system_performance': latest_snapshot.__dict__ if latest_snapshot else {},
            'application_metrics': {
                name: {
                    'value': metric.value,
                    'type': metric.metric_type.value,
                    'description': metric.description,
                    'tags': metric.tags
                }
                for name, metric in metrics.items()
            },
            'averages_5min': recent_metrics,
            'collector_stats': {
                'snapshot_count': len(self.collector.get_snapshots()),
                'collection_interval': self.collector.collection_interval
            }
        }

        return report

    def export_report(self, file_path: str, format: str = 'json'):
        """导出性能报告"""
        report = self.get_comprehensive_report()

        if format.lower() == 'json':
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()
