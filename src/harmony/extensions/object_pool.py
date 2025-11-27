"""
对象池 - 减少频繁创建销毁对象的开销
"""

import threading
import time
import weakref
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Type, Any, Callable


@dataclass
class PoolStatistics:
    """池统计信息"""
    total_created: int = 0
    total_reused: int = 0
    current_size: int = 0
    max_size: int = 0
    hit_rate: float = 0.0
    avg_creation_time: float = 0.0


class ObjectPool:
    """通用对象池"""

    def __init__(self,
                 object_type: Type,
                 factory: Callable[[], Any],
                 reset_func: Optional[Callable[[Any], None]] = None,
                 max_size: int = 100,
                 min_size: int = 5,
                 max_idle_time: float = 300.0):
        self.object_type = object_type
        self.factory = factory
        self.reset_func = reset_func
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time

        self._pool = deque()
        self._in_use = weakref.WeakSet()
        self._created_timestamps = weakref.WeakKeyDictionary()
        self._lock = threading.RLock()

        self._stats = PoolStatistics()
        self._creation_times = deque(maxlen=100)  # 保留最近100次的创建时间

        # 预热池
        self._warm_up()

    def _warm_up(self):
        """预热对象池"""
        for _ in range(self.min_size):
            obj = self.factory()
            self._created_timestamps[obj] = time.time()
            self._pool.append(obj)
            self._stats.total_created += 1

    def get_object(self) -> Any:
        """从池中获取对象"""
        with self._lock:
            # 尝试从池中获取
            if self._pool:
                obj = self._pool.popleft()
                self._created_timestamps[obj] = time.time()
                self._stats.total_reused += 1
                self._stats.current_size = len(self._pool)
            else:
                # 池为空，创建新对象
                start_time = time.time()
                obj = self.factory()
                creation_time = time.time() - start_time
                self._creation_times.append(creation_time)

                self._stats.total_created += 1
                self._stats.current_size = len(self._pool)

            self._in_use.add(obj)
            self._update_statistics()

            return obj

    def return_object(self, obj: Any):
        """将对象返回池中"""
        with self._lock:
            if obj not in self._in_use:
                return  # 对象不属于此池

            # 重置对象状态
            if self.reset_func:
                try:
                    self.reset_func(obj)
                except Exception as e:
                    # 重置失败，不放回池中
                    self._in_use.discard(obj)
                    return

            # 检查池大小限制
            if len(self._pool) < self.max_size:
                self._pool.append(obj)
                self._stats.current_size = len(self._pool)
            else:
                # 池已满，丢弃对象
                pass

            self._in_use.discard(obj)
            self._update_statistics()

    def cleanup_idle_objects(self):
        """清理闲置时间过长的对象"""
        current_time = time.time()
        objects_to_remove = []

        with self._lock:
            # 扫描池中的对象
            temp_pool = deque()
            for obj in self._pool:
                creation_time = self._created_timestamps.get(obj, current_time)
                if current_time - creation_time > self.max_idle_time:
                    objects_to_remove.append(obj)
                else:
                    temp_pool.append(obj)

            self._pool = temp_pool
            self._stats.current_size = len(self._pool)

        return len(objects_to_remove)

    def _update_statistics(self):
        """更新统计信息"""
        total_requests = self._stats.total_created + self._stats.total_reused
        if total_requests > 0:
            self._stats.hit_rate = self._stats.total_reused / total_requests

        if self._creation_times:
            self._stats.avg_creation_time = sum(self._creation_times) / len(self._creation_times)

        self._stats.max_size = max(self._stats.max_size, len(self._pool))

    def get_statistics(self) -> PoolStatistics:
        """获取池统计信息"""
        with self._lock:
            # 更新当前统计
            self._stats.current_size = len(self._pool)
            return PoolStatistics(
                total_created=self._stats.total_created,
                total_reused=self._stats.total_reused,
                current_size=self._stats.current_size,
                max_size=self._stats.max_size,
                hit_rate=self._stats.hit_rate,
                avg_creation_time=self._stats.avg_creation_time
            )

    def clear(self):
        """清空对象池"""
        with self._lock:
            self._pool.clear()
            self._in_use.clear()
            self._created_timestamps.clear()
            self._stats = PoolStatistics()

    def resize(self, new_max_size: int, new_min_size: int):
        """调整池大小"""
        with self._lock:
            old_max_size = self.max_size
            old_min_size = self.min_size

            self.max_size = new_max_size
            self.min_size = new_min_size

            # 如果新最大尺寸更小，移除多余对象
            while len(self._pool) > self.max_size:
                self._pool.popleft()

            # 如果新最小尺寸更大，添加对象
            while len(self._pool) < self.min_size:
                obj = self.factory()
                self._pool.append(obj)
                self._stats.total_created += 1


class PrototypeObjectPool:
    """原型Bean对象池管理器"""

    def __init__(self,
                 default_max_size: int = 50,
                 default_min_size: int = 5,
                 cleanup_interval: float = 60.0):
        self.default_max_size = default_max_size
        self.default_min_size = default_min_size
        self.cleanup_interval = cleanup_interval

        self._pools: Dict[Type, ObjectPool] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False

        self._start_cleanup_thread()

    def get_pool(self, bean_type: Type, factory: Callable[[], Any]) -> ObjectPool:
        """获取或创建对象池"""
        with self._lock:
            if bean_type not in self._pools:
                self._pools[bean_type] = ObjectPool(
                    object_type=bean_type,
                    factory=factory,
                    max_size=self.default_max_size,
                    min_size=self.default_min_size
                )
            return self._pools[bean_type]

    def get_prototype_instance(self, bean_type: Type, factory: Callable[[], Any]) -> Any:
        """获取原型Bean实例（使用对象池）"""
        pool = self.get_pool(bean_type, factory)
        return pool.get_object()

    def return_prototype_instance(self, bean_type: Type, instance: Any):
        """返回原型Bean实例到池中"""
        with self._lock:
            if bean_type in self._pools:
                self._pools[bean_type].return_object(instance)

    def _start_cleanup_thread(self):
        """启动清理线程"""
        if not self._running:
            self._running = True
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True
            )
            self._cleanup_thread.start()

    def _cleanup_worker(self):
        """清理工作线程"""
        while self._running:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_all_pools()
            except Exception as e:
                # 记录错误但继续运行
                pass

    def _cleanup_all_pools(self):
        """清理所有对象池的闲置对象"""
        with self._lock:
            for pool in self._pools.values():
                pool.cleanup_idle_objects()

    def get_all_statistics(self) -> Dict[Type, PoolStatistics]:
        """获取所有池的统计信息"""
        with self._lock:
            return {bean_type: pool.get_statistics()
                    for bean_type, pool in self._pools.items()}

    def resize_pool(self, bean_type: Type, max_size: int, min_size: int):
        """调整特定对象池的大小"""
        with self._lock:
            if bean_type in self._pools:
                self._pools[bean_type].resize(max_size, min_size)

    def clear_pool(self, bean_type: Type):
        """清空特定对象池"""
        with self._lock:
            if bean_type in self._pools:
                self._pools[bean_type].clear()
                del self._pools[bean_type]

    def clear_all_pools(self):
        """清空所有对象池"""
        with self._lock:
            for pool in self._pools.values():
                pool.clear()
            self._pools.clear()

    def shutdown(self):
        """关闭对象池管理器"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        self.clear_all_pools()

    def __del__(self):
        """析构函数"""
        self.shutdown()


# 全局原型对象池实例
prototype_object_pool = PrototypeObjectPool()
