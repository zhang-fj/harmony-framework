"""
反射缓存 - 缓存反射操作结果以提升性能
"""

import inspect
import threading
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List


@dataclass
class ConstructorInfo:
    """构造器信息"""
    parameters: List[Tuple[str, type, bool, Any]]  # (name, type, required, default)
    signature: inspect.Signature


@dataclass
class MethodInfo:
    """方法信息"""
    name: str
    parameters: List[Tuple[str, type, Any]]
    return_type: Optional[type]


@dataclass
class FieldInfo:
    """字段信息"""
    name: str
    field_type: type
    is_optional: bool


class ReflectionCache:
    """反射结果缓存"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._constructor_cache: Dict[type, ConstructorInfo] = {}
        self._method_cache: Dict[type, Dict[str, MethodInfo]] = {}
        self._field_cache: Dict[type, Dict[str, FieldInfo]] = {}
        self._annotation_cache: Dict[type, Dict[str, Any]] = {}
        self._access_count = {}
        self._lock = threading.RLock()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_constructor_info(self, cls: type) -> ConstructorInfo:
        """获取构造器信息（带缓存）"""
        with self._lock:
            if cls in self._constructor_cache:
                self._cache_hits += 1
                self._access_count[cls] = self._access_count.get(cls, 0) + 1
                return self._constructor_cache[cls]

            # 缓存未命中，执行反射
            self._cache_misses += 1
            constructor_info = self._analyze_constructor(cls)

            # 检查缓存大小，必要时清理
            if len(self._constructor_cache) >= self.max_size:
                self._evict_lru_constructors()

            self._constructor_cache[cls] = constructor_info
            self._access_count[cls] = 1
            return constructor_info

    def _analyze_constructor(self, cls: type) -> ConstructorInfo:
        """分析构造器"""
        try:
            signature = inspect.signature(cls.__init__)
            parameters = []

            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                # 跳过 *args 和 **kwargs
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue

                param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
                required = param.default == inspect.Parameter.empty
                default_value = param.default if not required else None

                parameters.append((param_name, param_type, required, default_value))

            return ConstructorInfo(parameters=parameters, signature=signature)

        except Exception as e:
            # 如果反射失败，返回默认构造器信息
            return ConstructorInfo(parameters=[], signature=None)

    def get_method_info(self, cls: type, method_name: str) -> Optional[MethodInfo]:
        """获取方法信息（带缓存）"""
        with self._lock:
            if cls in self._method_cache and method_name in self._method_cache[cls]:
                self._cache_hits += 1
                return self._method_cache[cls][method_name]

            self._cache_misses += 1

            method_info = self._analyze_method(cls, method_name)

            if method_info:
                if cls not in self._method_cache:
                    self._method_cache[cls] = {}
                self._method_cache[cls][method_name] = method_info

            return method_info

    def _analyze_method(self, cls: type, method_name: str) -> Optional[MethodInfo]:
        """分析方法"""
        try:
            if not hasattr(cls, method_name):
                return None

            method = getattr(cls, method_name)
            if not callable(method):
                return None

            signature = inspect.signature(method)
            parameters = []

            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
                default_value = param.default if param.default != inspect.Parameter.empty else None
                parameters.append((param_name, param_type, default_value))

            return_type = signature.return_annotation if signature.return_annotation != inspect.Signature.empty else None

            return MethodInfo(
                name=method_name,
                parameters=parameters,
                return_type=return_type
            )

        except Exception:
            return None

    def get_annotations(self, cls: type) -> Dict[str, Any]:
        """获取类注解（带缓存）"""
        with self._lock:
            if cls in self._annotation_cache:
                self._cache_hits += 1
                return self._annotation_cache[cls]

            self._cache_misses += 1
            annotations = {}

            # 收集所有Harmony相关注解
            harmony_attrs = [attr for attr in dir(cls) if 'harmony' in attr]
            for attr in harmony_attrs:
                try:
                    annotations[attr] = getattr(cls, attr)
                except:
                    continue

            # 检查缓存大小
            if len(self._annotation_cache) >= self.max_size:
                self._evict_lru_annotations()

            self._annotation_cache[cls] = annotations
            return annotations

    def _evict_lru_constructors(self):
        """清理最少使用的构造器缓存"""
        if not self._constructor_cache:
            return

        # 按访问次数排序，移除最少使用的25%
        sorted_items = sorted(self._access_count.items(), key=lambda x: x[1])
        evict_count = max(1, len(sorted_items) // 4)

        for cls, _ in sorted_items[:evict_count]:
            self._constructor_cache.pop(cls, None)
            self._access_count.pop(cls, None)

    def _evict_lru_annotations(self):
        """清理最少使用的注解缓存"""
        if len(self._annotation_cache) <= self.max_size * 0.8:
            return

        # 简单策略：移除前20%的缓存
        items_to_remove = list(self._annotation_cache.keys())[:self.max_size // 5]
        for cls in items_to_remove:
            self._annotation_cache.pop(cls, None)

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

            return {
                'constructor_cache_size': len(self._constructor_cache),
                'method_cache_size': sum(len(methods) for methods in self._method_cache.values()),
                'annotation_cache_size': len(self._annotation_cache),
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._constructor_cache.clear()
            self._method_cache.clear()
            self._annotation_cache.clear()
            self._access_count.clear()
            self._cache_hits = 0
            self._cache_misses = 0

    def optimize_for_current_usage(self):
        """根据当前使用模式优化缓存"""
        with self._lock:
            # 预加载高频访问的类
            if self._access_count:
                # 找出访问频率最高的类
                sorted_classes = sorted(self._access_count.items(), key=lambda x: x[1], reverse=True)
                top_classes = sorted_classes[:min(10, len(sorted_classes))]

                for cls, count in top_classes:
                    if count > 10:  # 高频访问的类
                        # 预加载相关方法信息
                        self._preload_common_methods(cls)

    def _preload_common_methods(self, cls: type):
        """预加载常用方法信息"""
        common_methods = ['__init__', '__post_construct__', '__destroy__']
        for method_name in common_methods:
            self.get_method_info(cls, method_name)


# 全局反射缓存实例
reflection_cache = ReflectionCache()
