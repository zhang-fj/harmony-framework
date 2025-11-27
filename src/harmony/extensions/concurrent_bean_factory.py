"""
并发安全的Bean工厂 - 优化高并发场景下的性能
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Type, Set

from .object_pool import prototype_object_pool
from .reflection_cache import reflection_cache
from ..core.bean_definition import BeanDefinition
from ..core.scope import ScopeType
from ..exceptions.harmony_exceptions import (
    NoSuchBeanDefinitionException,
    BeanCreationException,
    CircularDependencyException
)

try:
    from ..utils.logger import get_logger
except ImportError:
    import logging


    def get_logger(name):
        return logging.getLogger(name)


class ConcurrentBeanFactory:
    """并发优化的Bean工厂"""

    def __init__(self, num_segments: int = 16):
        self.num_segments = num_segments
        self.bean_definitions: Dict[str, BeanDefinition] = {}
        self.type_to_bean_names: Dict[Type, List[str]] = {}

        # 分段锁策略
        self._segment_locks = [threading.RLock() for _ in range(num_segments)]
        self._singleton_segments = [{} for _ in range(num_segments)]
        self._creation_locks = {}  # 每个Bean的创建锁

        # 循环依赖检测
        self._creating_beans: Set[str] = set()
        self._dependency_lock = threading.RLock()

        # 读写分离的元数据锁
        self._metadata_lock = threading.RLock()

        # 性能统计
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'concurrent_creations': 0,
            'lock_contentions': 0
        }

        self.logger = get_logger('concurrent_bean_factory')

    def _get_segment_index(self, key: str) -> int:
        """获取key对应的段索引"""
        return hash(key) % self.num_segments

    def _get_segment_lock(self, key: str) -> threading.RLock:
        """获取key对应的段锁"""
        segment_index = self._get_segment_index(key)
        return self._segment_locks[segment_index]

    def _get_singleton_segment(self, bean_name: str) -> Dict[str, Any]:
        """获取Bean对应的单例段"""
        segment_index = self._get_segment_index(bean_name)
        return self._singleton_segments[segment_index]

    def _get_creation_lock(self, bean_name: str) -> threading.Lock:
        """获取Bean创建锁"""
        if bean_name not in self._creation_locks:
            with self._dependency_lock:
                if bean_name not in self._creation_locks:
                    self._creation_locks[bean_name] = threading.Lock()
        return self._creation_locks[bean_name]

    def register_bean_definition(self, definition: BeanDefinition) -> None:
        """注册Bean定义（线程安全）"""
        with self._metadata_lock:
            # 注册Bean定义
            self.bean_definitions[definition.bean_name] = definition

            # 更新类型映射
            bean_type = definition.bean_type
            if bean_type not in self.type_to_bean_names:
                self.type_to_bean_names[bean_type] = []
            self.type_to_bean_names[bean_type].append(definition.bean_name)

        self.logger.debug(f"Registered bean definition: {definition}")

    def get_bean(self, bean_name: str) -> Any:
        """获取Bean实例（并发优化）"""
        # 首先检查是否存在定义
        if not self._contains_bean_definition(bean_name):
            raise NoSuchBeanDefinitionException(bean_name)

        definition = self.bean_definitions[bean_name]

        if definition.scope == ScopeType.SINGLETON:
            return self._get_singleton_bean(definition)
        elif definition.scope == ScopeType.PROTOTYPE:
            return self._get_prototype_bean(definition)
        else:
            raise BeanCreationException(bean_name, f"Unsupported scope: {definition.scope}")

    def _contains_bean_definition(self, bean_name: str) -> bool:
        """线程安全地检查Bean定义是否存在"""
        with self._metadata_lock:
            return bean_name in self.bean_definitions

    def _get_singleton_bean(self, definition: BeanDefinition) -> Any:
        """获取单例Bean（并发优化）"""
        bean_name = definition.bean_name
        segment = self._get_singleton_segment(bean_name)

        # 快速路径：无锁读取
        if bean_name in segment:
            self._stats['cache_hits'] += 1
            return segment[bean_name]

        # 慢速路径：需要创建
        creation_lock = self._get_creation_lock(bean_name)
        acquired = creation_lock.acquire(blocking=False)

        if acquired:
            try:
                # 双重检查
                if bean_name in segment:
                    return segment[bean_name]

                # 创建Bean
                instance = self._create_bean_with_circular_detection(definition)

                # 原子性地放入缓存
                with self._get_segment_lock(bean_name):
                    segment[bean_name] = instance

                return instance

            finally:
                creation_lock.release()
        else:
            # 等待其他线程创建完成
            self._stats['lock_contentions'] += 1
            creation_lock.acquire()
            creation_lock.release()

            # 再次检查缓存
            if bean_name in segment:
                return segment[bean_name]
            else:
                # 创建失败，抛出异常
                raise BeanCreationException(bean_name, "Failed to create singleton bean")

    def _get_prototype_bean(self, definition: BeanDefinition) -> Any:
        """获取原型Bean（使用对象池优化）"""
        bean_name = definition.bean_name
        bean_type = definition.bean_type

        # 检查循环依赖
        with self._dependency_lock:
            if bean_name in self._creating_beans:
                raise CircularDependencyException(bean_name, list(self._creating_beans))

        # 创建工厂函数
        def factory():
            return self._create_bean_with_circular_detection(definition)

        # 使用对象池
        try:
            with self._dependency_lock:
                self._creating_beans.add(bean_name)

            instance = prototype_object_pool.get_prototype_instance(bean_type, factory)
            return instance

        finally:
            with self._dependency_lock:
                self._creating_beans.discard(bean_name)

    def _create_bean_with_circular_detection(self, definition: BeanDefinition) -> Any:
        """带循环依赖检测的Bean创建"""
        bean_name = definition.bean_name

        # 使用反射缓存优化
        constructor_info = reflection_cache.get_constructor_info(definition.bean_type)

        try:
            # 使用工厂方法创建实例
            if definition.factory_method:
                instance = definition.factory_method()
            elif constructor_info.parameters:
                # 构造器注入
                constructor_deps = self._resolve_constructor_dependencies(definition, constructor_info)
                instance = definition.bean_type(*[dep[1] for dep in constructor_deps])
            else:
                # 直接创建实例
                instance = definition.bean_type()

            # 执行依赖注入和初始化
            self._perform_injection_and_initialization(instance, definition)

            return instance

        except Exception as e:
            self.logger.error(f"Failed to create bean {bean_name}: {e}")
            raise BeanCreationException(bean_name, str(e), cause=e)

    def _resolve_constructor_dependencies(self, definition: BeanDefinition, constructor_info) -> List[Any]:
        """解析构造器依赖（优化版）"""
        dependencies = []

        for param_name, param_type, required, default_value in constructor_info.parameters:
            # 检查是否为基础数据类型
            if param_type in (bool, str, int, float, dict, list):
                dependencies.append(default_value)
                continue

            # 查找对应的构造器参数定义
            constructor_arg = None
            for arg in definition.constructor_args:
                if arg.name == param_name:
                    constructor_arg = arg
                    break

            if constructor_arg and constructor_arg.qualifier:
                # 使用限定符查找
                dep = self.get_bean(constructor_arg.qualifier)
            else:
                # 使用类型查找
                dep = self.get_bean_by_type(param_type)

            dependencies.append(dep)

        return dependencies

    def _perform_injection_and_initialization(self, instance: Any, definition: BeanDefinition):
        """执行依赖注入和初始化"""
        # 自动注入autowired字段
        self._inject_autowired_fields(instance, definition)

        # 注入setter依赖
        self._inject_setter_dependencies(instance, definition)

        # 调用初始化方法
        if definition.init_method:
            init_method = getattr(instance, definition.init_method)
            init_method()

        # 调用PostConstruct方法
        self._invoke_post_construct_methods(instance)

    def _inject_autowired_fields(self, instance: Any, definition: BeanDefinition):
        """注入autowired标记的字段"""
        bean_class = definition.bean_type

        if hasattr(bean_class, '__harmony_autowired_fields__'):
            autowired_fields = bean_class.__harmony_autowired_fields__

            for field_name, bean_name in autowired_fields.items():
                bean_instance = self.get_bean(bean_name)
                setattr(instance, field_name, bean_instance)

    def _inject_setter_dependencies(self, instance: Any, definition: BeanDefinition):
        """注入setter依赖"""
        for dep in definition.setter_dependencies:
            try:
                if dep.qualifier:
                    dependency = self.get_bean(dep.qualifier)
                else:
                    dependency = self.get_bean_by_type(dep.dependency_type)

                # 调用setter方法
                setter_name = f"set_{dep.name[0].upper()}{dep.name[1:]}"
                if hasattr(instance, setter_name):
                    setter_method = getattr(instance, setter_name)
                    setter_method(dependency)
                else:
                    self.logger.warning(f"Setter method {setter_name} not found on {type(instance)}")

            except Exception as e:
                if dep.required:
                    raise Exception(f"Failed to inject setter dependency '{dep.name}': {e}")

    def _invoke_post_construct_methods(self, instance: Any):
        """调用PostConstruct方法"""
        # 使用反射缓存获取方法信息
        bean_class = instance.__class__
        methods_info = reflection_cache.get_method_info(bean_class, '__post_construct__')

        if methods_info:
            try:
                post_construct_method = getattr(instance, '__post_construct__')
                post_construct_method()
                return
            except Exception:
                pass

        # 检查其他PostConstruct注解的方法
        annotations = reflection_cache.get_annotations(bean_class)
        for attr_name, attr_value in annotations.items():
            if 'post_construct' in attr_name.lower():
                try:
                    method = getattr(instance, attr_name.replace('__harmony_', ''))
                    method()
                    break
                except Exception:
                    pass

    def get_bean_by_type(self, bean_type: Type, qualifier: Optional[str] = None) -> Any:
        """通过类型获取Bean实例"""
        with self._metadata_lock:
            if bean_type not in self.type_to_bean_names:
                raise NoSuchBeanDefinitionException(f"No bean of type {bean_type} found")
            candidate_names = self.type_to_bean_names[bean_type]

        if qualifier:
            if qualifier in candidate_names:
                return self.get_bean(qualifier)
            else:
                raise NoSuchBeanDefinitionException(f"No bean with qualifier '{qualifier}' found")

        if len(candidate_names) == 1:
            return self.get_bean(candidate_names[0])

        # 查找primary候选
        primary_candidates = [
            name for name in candidate_names
            if self.bean_definitions[name].primary
        ]

        if len(primary_candidates) == 1:
            return self.get_bean(primary_candidates[0])
        else:
            raise BeanCreationException(
                "multiple_candidates",
                f"Multiple beans found for type {bean_type}: {candidate_names}. Please use qualifier."
            )

    def contains_bean(self, bean_name: str) -> bool:
        """检查是否包含指定名称的Bean"""
        return self._contains_bean_definition(bean_name)

    def get_bean_names(self) -> List[str]:
        """获取所有Bean名称"""
        with self._metadata_lock:
            return list(self.bean_definitions.keys())

    def pre_instantiate_singletons(self) -> None:
        """预实例化所有非延迟的单例Bean（并发优化）"""
        with self._metadata_lock:
            bean_definitions = list(self.bean_definitions.items())

        # 使用线程池并发创建
        with ThreadPoolExecutor(max_workers=min(10, len(bean_definitions))) as executor:
            futures = []

            for bean_name, definition in bean_definitions:
                if (definition.scope == ScopeType.SINGLETON and
                        not definition.lazy):
                    future = executor.submit(self._safe_pre_instantiate, bean_name, definition)
                    futures.append(future)

            # 等待所有创建完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Failed to pre-instantiate bean: {e}")

    def _safe_pre_instantiate(self, bean_name: str, definition: BeanDefinition):
        """安全的预实例化"""
        try:
            self.logger.debug(f"Pre-instantiating singleton bean: {bean_name}")
            self.get_bean(bean_name)
        except Exception as e:
            self.logger.error(f"Failed to pre-instantiate bean {bean_name}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        reflection_stats = reflection_cache.get_cache_stats()
        pool_stats = prototype_object_pool.get_all_statistics()

        return {
            'bean_count': len(self.bean_definitions),
            'singleton_segments': len(self._singleton_segments),
            'creation_locks': len(self._creation_locks),
            'reflection_cache': reflection_stats,
            'object_pools': {str(k): v for k, v in pool_stats.items()},
            'internal_stats': self._stats.copy()
        }

    def cleanup(self):
        """清理资源"""
        prototype_object_pool.shutdown()
        reflection_cache.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
