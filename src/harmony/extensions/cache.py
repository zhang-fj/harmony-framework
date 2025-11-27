"""
扫描缓存模块 - 优化版本，用于提升组件扫描性能
"""

import hashlib
import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import OrderedDict
from weakref import WeakKeyDictionary

from ..core.bean_definition import BeanDefinition


@dataclass
class CacheEntry:
    """优化的缓存条目"""
    bean_definitions: List[BeanDefinition] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    scan_hash: str = field(default="")
    file_mtimes: Dict[str, float] = field(default_factory=dict)
    access_count: int = 0

    def is_expired(self, max_age_seconds: int = 300) -> bool:
        """检查缓存是否过期"""
        return time.time() - self.timestamp > max_age_seconds

    def is_valid(self, current_hash: str, current_mtimes: Dict[str, float]) -> bool:
        """检查缓存是否仍然有效"""
        if self.scan_hash != current_hash:
            return False
        if self.is_expired():
            return False

        # 检查关键文件修改时间
        for file_path, mtime in current_mtimes.items():
            if file_path in self.file_mtimes:
                if abs(self.file_mtimes[file_path] - mtime) > 1.0:  # 1秒容差
                    return False

        return True

    def record_access(self) -> None:
        """记录访问"""
        self.access_count += 1


class OptimizedScanCache:
    """优化的组件扫描缓存管理器"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl

        # 使用OrderedDict实现LRU缓存
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'errors': 0
        }

        # 线程安全
        self._lock = threading.RLock()

        # 文件变化监控
        self._file_hash_cache: Dict[str, Tuple[str, float]] = {}

    def _calculate_file_hash_fast(self, file_path: str) -> Tuple[str, float]:
        """快速计算文件哈希（基于元数据）"""
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size

            # 检查缓存
            cache_key = file_path
            if cache_key in self._file_hash_cache:
                cached_hash, cached_mtime = self._file_hash_cache[cache_key]
                if abs(cached_mtime - mtime) < 1.0:  # 1秒容差
                    return cached_hash, mtime

            # 计算新的哈希
            hash_input = f"{file_path}:{mtime}:{size}"
            file_hash = hashlib.md5(hash_input.encode()).hexdigest()

            # 缓存结果
            self._file_hash_cache[cache_key] = (file_hash, mtime)

            # 限制文件哈希缓存大小
            if len(self._file_hash_cache) > self.max_size * 2:
                # 清理最旧的缓存项
                old_keys = sorted(self._file_hash_cache.keys(),
                                key=lambda k: self._file_hash_cache[k][1])[:len(self._file_hash_cache) // 2]
                for key in old_keys:
                    del self._file_hash_cache[key]

            return file_hash, mtime

        except (OSError, IOError) as e:
            self._stats['errors'] += 1
            return "", 0.0

    def _calculate_directory_hash_optimized(self, package_path: Path) -> Tuple[str, Dict[str, float]]:
        """优化的目录哈希计算"""
        hash_obj = hashlib.md5()
        file_mtimes: Dict[str, float] = {}
        python_files: List[str] = []

        try:
            for root, dirs, files in os.walk(package_path):
                # 跳过__pycache__目录和其他临时目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'node_modules']

                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = os.path.join(root, file)
                        python_files.append(file_path)

            # 对文件排序以确保一致性
            python_files.sort()

            # 并行计算文件哈希（限制并发数）
            for file_path in python_files:
                file_hash, mtime = self._calculate_file_hash_fast(file_path)
                if file_hash:
                    hash_obj.update(file_hash.encode())
                    file_mtimes[file_path] = mtime

            return hash_obj.hexdigest(), file_mtimes

        except (OSError, IOError) as e:
            self._stats['errors'] += 1
            return "", {}

    def get(self, package_name: str, package_path: Path) -> Optional[List[BeanDefinition]]:
        """获取缓存的扫描结果（优化版）"""
        cache_key = f"{package_name}:{str(package_path)}"

        with self._lock:
            self._stats['misses'] += 1

            if cache_key not in self._cache:
                return None

            # 计算当前目录哈希
            current_hash, current_mtimes = self._calculate_directory_hash_optimized(package_path)
            if not current_hash:
                return None

            cache_entry = self._cache[cache_key]

            # 检查缓存有效性
            if cache_entry.is_valid(current_hash, current_mtimes):
                # 移动到最前面（LRU更新）
                self._cache.move_to_end(cache_key)
                cache_entry.record_access()

                # 更新统计
                self._stats['hits'] += 1
                self._stats['misses'] -= 1  # 修正误计数

                return cache_entry.bean_definitions.copy()  # 返回副本避免修改

            # 缓存失效，清理
            del self._cache[cache_key]
            return None

    def put(self, package_name: str, package_path: Path, bean_definitions: List[BeanDefinition]):
        """缓存扫描结果（优化版）"""
        if not bean_definitions:
            return  # 不缓存空结果

        cache_key = f"{package_name}:{str(package_path)}"

        with self._lock:
            # 如果缓存已满，移除最少使用的条目
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # 移除最旧的（LRU）
                self._stats['evictions'] += 1

            # 计算当前目录哈希
            current_hash, current_mtimes = self._calculate_directory_hash_optimized(package_path)
            if not current_hash:
                return

            cache_entry = CacheEntry(
                bean_definitions=bean_definitions.copy(),  # 存储副本
                timestamp=time.time(),
                scan_hash=current_hash,
                file_mtimes=current_mtimes,
                access_count=1
            )

            self._cache[cache_key] = cache_entry
            self._cache.move_to_end(cache_key)  # 新条目移到最后

    def clear(self):
        """清空缓存（线程安全）"""
        with self._lock:
            self._cache.clear()
            self._file_hash_cache.clear()
            # 重置统计
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'errors': 0
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息（线程安全）"""
        with self._lock:
            total_access = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / max(total_access, 1)

            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_count': self._stats['hits'],
                'miss_count': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'errors': self._stats['errors'],
                'file_hash_cache_size': len(self._file_hash_cache),
                'memory_usage_estimate': self._estimate_memory_usage()
            }

    def _estimate_memory_usage(self) -> int:
        """估算内存使用量（字节）"""
        # 粗略估算
        cache_memory = len(self._cache) * 1024  # 假设每个缓存项1KB
        file_hash_memory = len(self._file_hash_cache) * 256  # 假设每个文件哈希256字节
        return cache_memory + file_hash_memory

    def optimize_for_current_usage(self):
        """根据当前使用模式优化缓存"""
        with self._lock:
            # 清理未使用的文件哈希缓存
            current_time = time.time()
            stale_keys = [
                key for key, (_, mtime) in self._file_hash_cache.items()
                if current_time - mtime > 3600  # 1小时未使用
            ]

            for key in stale_keys:
                del self._file_hash_cache[key]

            # 清理访问次数过少的缓存项
            if len(self._cache) > self.max_size * 0.8:  # 如果使用率超过80%
                # 保留访问次数最多的条目
                sorted_items = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].access_count,
                    reverse=True
                )

                # 保留前80%的条目
                keep_count = int(len(sorted_items) * 0.8)
                self._cache = OrderedDict(sorted_items[:keep_count])


class MetadataCache:
    """优化的类元数据缓存"""

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        # 使用WeakKeyDictionary避免内存泄漏
        self._class_metadata: WeakKeyDictionary = WeakKeyDictionary()
        # 使用OrderedDict实现LRU
        self._access_order: OrderedDict[int, type] = OrderedDict()
        self._access_counter = 0
        self._lock = threading.RLock()

    def get_class_info(self, cls: type) -> Optional[Dict]:
        """获取类信息缓存（线程安全）"""
        with self._lock:
            if cls in self._class_metadata:
                # 更新访问顺序
                self._access_counter += 1
                self._access_order[self._access_counter] = cls

                # 清理旧的访问记录
                if len(self._access_order) > self.max_size * 2:
                    old_keys = list(self._access_order.keys())[:len(self._access_order) // 2]
                    for key in old_keys:
                        self._access_order.pop(key, None)

                return self._class_metadata[cls].copy()  # 返回副本
            return None

    def put_class_info(self, cls: type, metadata: Dict):
        """缓存类信息（线程安全）"""
        if not metadata:
            return

        with self._lock:
            # 检查缓存大小
            if len(self._class_metadata) >= self.max_size:
                self._evict_lru()

            self._class_metadata[cls] = metadata.copy()

            # 更新访问顺序
            self._access_counter += 1
            self._access_order[self._access_counter] = cls

    def _evict_lru(self):
        """移除最少使用的类元数据"""
        if not self._access_order:
            return

        # 移除最旧的访问记录对应的类
        oldest_key = min(self._access_order.keys())
        oldest_class = self._access_order[oldest_key]

        self._class_metadata.pop(oldest_class, None)
        self._access_order.pop(oldest_key, None)

    def clear(self):
        """清空缓存（线程安全）"""
        with self._lock:
            self._class_metadata.clear()
            self._access_order.clear()
            self._access_counter = 0

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'cache_size': len(self._class_metadata),
                'max_size': self.max_size,
                'access_records': len(self._access_order)
            }


# 全局优化缓存实例
scan_cache = OptimizedScanCache()
metadata_cache = MetadataCache()