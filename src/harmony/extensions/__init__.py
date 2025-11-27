"""
Harmony扩展模块 - 优化和高级功能
"""

# 直接导入常用的、轻量级的组件
from .cache import CacheEntry, OptimizedScanCache as ScanCache, MetadataCache
from .object_pool import PoolStatistics, PrototypeObjectPool
from .reflection_cache import ConstructorInfo, MethodInfo, FieldInfo

# 延迟导入复杂的组件，避免循环依赖
def __getattr__(name: str):
    """
    延迟导入复杂组件，避免循环依赖和启动时间问题

    Args:
        name: 要导入的组件名称

    Returns:
        对应的类或实例

    Raises:
        AttributeError: 当组件不存在时

    Note:
        PyCharm可能无法正确识别这些动态导入，这是正常的。
        运行时导入工作正常，IDE警告可以忽略。
    """
    if name == 'ObjectPool':
        from .object_pool import ObjectPool
        return ObjectPool
    elif name == 'ReflectionCache':
        from .reflection_cache import ReflectionCache
        return ReflectionCache
    elif name == 'reflection_cache':
        from .reflection_cache import reflection_cache
        return reflection_cache
    elif name == 'LifecycleEventSystem':
        from .lifecycle_events import LifecycleEventSystem
        return LifecycleEventSystem
    elif name == 'lifecycle_event_system':
        from .lifecycle_events import lifecycle_event_system
        return lifecycle_event_system
    elif name == 'HotReloadManager':
        from .hot_reload import HotReloadManager
        return HotReloadManager
    elif name == 'hot_reload_manager':
        from .hot_reload import hot_reload_manager
        return hot_reload_manager
    elif name == 'PerformanceMonitor':
        from .performance_monitor import PerformanceMonitor
        return PerformanceMonitor
    elif name == 'performance_monitor':
        from .performance_monitor import performance_monitor
        return performance_monitor
    elif name == 'ConcurrentBeanFactory':
        from .concurrent_bean_factory import ConcurrentBeanFactory
        return ConcurrentBeanFactory
    elif name == 'DataSourceManager':
        from .data_source.manager import DataSourceManager
        return DataSourceManager
    elif name == 'get_data_source_manager':
        from .data_source.manager import get_data_source_manager
        return get_data_source_manager
    elif name == 'TransactionManager':
        from .data_source.transaction import TransactionManager
        return TransactionManager
    elif name == 'get_transaction_manager':
        from .data_source.transaction import get_transaction_manager
        return get_transaction_manager
    elif name == 'TransactionTemplate':
        from .data_source.transaction import TransactionTemplate
        return TransactionTemplate
    elif name == 'BaseRepository':
        from .data_source.repository import BaseRepository
        return BaseRepository
    elif name == 'SimpleRepository':
        from .data_source.repository import SimpleRepository
        return SimpleRepository
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # 直接导入的轻量级组件
    'CacheEntry',
    'ScanCache',
    'MetadataCache',
    'PoolStatistics',
    'PrototypeObjectPool',
    'ConstructorInfo',
    'MethodInfo',
    'FieldInfo',

    # 延迟导入的复杂组件
    'ObjectPool',
    'ReflectionCache',
    'reflection_cache',
    'LifecycleEventSystem',
    'lifecycle_event_system',
    'HotReloadManager',
    'hot_reload_manager',
    'PerformanceMonitor',
    'performance_monitor',
    'ConcurrentBeanFactory',
    'DataSourceManager',
    'get_data_source_manager',
    'TransactionManager',
    'get_transaction_manager',
    'TransactionTemplate',
    'BaseRepository',
    'SimpleRepository'
]
