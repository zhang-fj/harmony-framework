import difflib
import inspect
import threading
import weakref
from typing import Dict, Any, List, Optional, Type, TypeVar

from .bean_definition import BeanDefinition
from ..annotations import LifecycleManager, LifecyclePhase
from ..container.scope import ScopeType
from ..exceptions.harmony_exceptions import (
    NoSuchBeanDefinitionException,
    BeanCreationException,
    DependencyInjectionException
)
from ..extensions.cache import scan_cache, metadata_cache
from ..extensions.object_pool import prototype_object_pool
from ..extensions.reflection_cache import reflection_cache
from ..utils.logger import get_logger, log_execution_time

# 泛型类型变量
T = TypeVar('T')


class BeanFactory:
    """Bean工厂 - 增强版，支持完整的类型安全"""

    def __init__(self):
        self.bean_definitions: Dict[str, BeanDefinition] = {}
        self.singleton_instances: Dict[str, Any] = {}
        # 使用弱引用追踪原型实例，避免内存泄漏
        self.prototype_instances: List[weakref.ref] = []
        self.type_to_bean_names: Dict[Type, List[str]] = {}
        self._creation_lock = threading.RLock()
        self._creating_beans: set = set()  # 循环依赖检测
        self.logger = get_logger('bean_factory')
        self.lifecycle_manager = LifecycleManager()  # 生命周期管理器
        self._cleanup_counter = 0  # 清理计数器
        self._cleanup_threshold = 100  # 清理阈值

    @log_execution_time(get_logger('bean_factory'))
    def register_bean_definition(self, definition: BeanDefinition) -> None:
        """注册Bean定义"""
        self.bean_definitions[definition.bean_name] = definition

        # 更新类型映射
        bean_type = definition.bean_type
        if bean_type not in self.type_to_bean_names:
            self.type_to_bean_names[bean_type] = []
        self.type_to_bean_names[bean_type].append(definition.bean_name)

        self.logger.debug(f"Registered bean definition: {definition}")

    def get_bean(self, bean_name: str) -> Any:
        """根据名称获取Bean实例"""
        if bean_name not in self.bean_definitions:
            # 提供相似的Bean名称建议
            available_names = list(self.bean_definitions.keys())
            suggested_names = self._find_similar_names(bean_name, available_names)
            available_types = list(self.type_to_bean_names.keys())
            raise NoSuchBeanDefinitionException(
                bean_name,
                suggested_names=suggested_names,
                available_types=available_types
            )

        definition = self.bean_definitions[bean_name]
        return self._get_bean_by_definition(definition)

    def get_bean_typed(self, bean_name: str, bean_type: Type[T]) -> T:
        """类型安全的Bean获取"""
        bean = self.get_bean(bean_name)
        if not isinstance(bean, bean_type):
            raise BeanCreationException(
                bean_name,
                f"Expected type {bean_type}, but got {type(bean)}"
            )
        return bean

    def get_bean_by_type(self, bean_type: Type[T], qualifier: Optional[str] = None) -> T:
        """通过类型获取Bean实例"""
        if bean_type not in self.type_to_bean_names:
            # 尝试查找子类
            candidates = self._find_subclass_candidates(bean_type)
            if not candidates:
                bean_type_name = getattr(bean_type, '__name__', str(bean_type))
                error_msg = f"No bean of type {bean_type_name} found"
                raise NoSuchBeanDefinitionException(error_msg, bean_type=bean_type_name)
            candidate_names = candidates
        else:
            candidate_names = self.type_to_bean_names[bean_type]

        if qualifier:
            if qualifier in candidate_names:
                return self.get_bean_typed(qualifier, bean_type)
            else:
                raise NoSuchBeanDefinitionException(f"No bean with qualifier '{qualifier}' found")

        # 如果只有一个候选，直接返回
        if len(candidate_names) == 1:
            return self.get_bean_typed(candidate_names[0], bean_type)

        # 查找primary候选
        primary_candidates = [
            name for name in candidate_names
            if self.bean_definitions[name].primary
        ]

        if len(primary_candidates) == 1:
            return self.get_bean_typed(primary_candidates[0], bean_type)
        elif len(primary_candidates) > 1:
            raise BeanCreationException(
                "multiple_primary",
                f"Multiple primary beans found for type {bean_type}: {primary_candidates}"
            )
        else:
            raise BeanCreationException(
                "multiple_candidates",
                f"Multiple beans found for type {bean_type}: {candidate_names}. Please use qualifier."
            )

    def _get_bean_by_definition(self, definition: BeanDefinition) -> Any:
        """根据Bean定义获取实例"""
        bean_name = definition.bean_name

        # 循环依赖检测
        if bean_name in self._creating_beans:
            raise BeanCreationException(
                bean_name,
                f"Circular dependency detected: currently creating beans: {self._creating_beans}"
            )

        with self._creation_lock:
            # 根据作用域创建或获取实例
            if definition.scope == ScopeType.SINGLETON:
                if bean_name not in self.singleton_instances:
                    instance = self._create_bean_instance(definition)
                    self.singleton_instances[bean_name] = instance
                return self.singleton_instances[bean_name]
            elif definition.scope == ScopeType.PROTOTYPE:
                return self._create_bean_instance(definition)
            else:
                raise BeanCreationException(bean_name, f"Unsupported scope: {definition.scope}")

    def _create_bean_instance(self, definition: BeanDefinition) -> Any:
        """创建Bean实例 - 支持构造器注入（优化版）"""
        self._creating_beans.add(definition.bean_name)

        try:
            # 使用对象池优化原型Bean创建
            if definition.scope == ScopeType.PROTOTYPE:
                return self._create_prototype_instance_with_pool(definition)

            # 使用反射缓存优化单例Bean创建
            instance = self._create_singleton_instance_with_cache(definition)

            # 如果是原型作用域，使用弱引用追踪实例
            if definition.scope == ScopeType.PROTOTYPE:
                self.prototype_instances.append(weakref.ref(instance))

            self.logger.debug(f"Created bean instance: {definition.bean_name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create bean {definition.bean_name}: {e}")
            raise BeanCreationException(definition.bean_name, str(e))
        finally:
            self._creating_beans.discard(definition.bean_name)

    def _create_singleton_instance_with_cache(self, definition: BeanDefinition) -> Any:
        """使用反射缓存创建单例Bean实例"""
        # 使用反射缓存获取构造器信息
        constructor_info = reflection_cache.get_constructor_info(definition.bean_type)

        # 使用工厂方法创建实例
        if definition.factory_method:
            instance = definition.factory_method()
        elif constructor_info.parameters:
            # 构造器注入 - 使用缓存的参数信息
            constructor_deps = self._resolve_constructor_dependencies_cached(definition, constructor_info)
            instance = definition.bean_type(*constructor_deps)
        else:
            # 直接创建实例
            instance = self._create_instance(definition.bean_type)

        # 统一的依赖注入处理
        self._perform_injection_and_initialization(instance, definition)

        return instance

    def _create_prototype_instance_with_pool(self, definition: BeanDefinition) -> Any:
        """使用对象池创建原型Bean实例"""
        bean_type = definition.bean_type

        # 创建工厂函数供对象池使用
        def factory():
            return self._create_singleton_instance_with_cache(definition)

        # 使用对象池获取实例
        try:
            instance = prototype_object_pool.get_prototype_instance(bean_type, factory)
            return instance
        except (OSError, ValueError, KeyError) as e:
            # 对象池失败时，回退到直接创建
            self.logger.debug(f"Object pool failed for {bean_type.__name__}, falling back to direct creation: {e}")
            return self._create_singleton_instance_with_cache(definition)

    def _resolve_constructor_dependencies_cached(self, definition: BeanDefinition, constructor_info) -> List[Any]:
        """使用缓存解析构造器依赖"""
        dependencies = []

        for param_name, param_type, required, default_value in constructor_info.parameters:
            # 检查是否为基础数据类型
            if param_type in (bool, str, int, float, dict, list):
                dependencies.append(default_value)
                continue

            # 查找对应的构造器参数定义
            qualifier = None
            for arg in definition.constructor_args:
                if arg.name == param_name:
                    qualifier = arg.qualifier
                    break

            # 解析依赖
            if qualifier:
                dep = self.get_bean(qualifier)
            elif (param_type and
                  param_type != type(None) and
                  param_type != object and
                  param_type != type(inspect.Parameter.empty)):
                dep = self.get_bean_by_type(param_type)
            else:
                # 如果没有明确的限定符、类型为空或为基础类型，使用默认值
                dep = None

            dependencies.append(dep)

        return dependencies

    def _perform_injection_and_initialization(self, instance: Any, definition: BeanDefinition):
        """统一的依赖注入和初始化处理"""
        # 自动注入autowired字段
        self._inject_autowired_fields(instance, definition)

        # 注入setter依赖
        self._inject_setter_dependencies(instance, definition)

        # 调用初始化方法
        if definition.init_method:
            init_method = getattr(instance, definition.init_method)
            init_method()

        # 调用PostConstruct方法 - 使用反射缓存优化
        self._invoke_post_construct_methods_cached(instance)

    def _invoke_post_construct_methods_cached(self, instance: Any):
        """调用PostConstruct方法（缓存优化版）"""
        bean_class = instance.__class__

        # 使用生命周期管理器扫描和处理生命周期回调
        bean_name = self._get_bean_name_for_instance(instance)
        if bean_name:
            self.lifecycle_manager.scan_class_callbacks(bean_class, bean_name)
            self.lifecycle_manager.execute_phase(bean_name, LifecyclePhase.INITIALIZATION, instance)

        # 检查是否有生命周期管理器处理，如果没有则使用兼容处理
        if not bean_name or not hasattr(self.lifecycle_manager, 'execute_phase'):
            # 直接扫描方法上的PostConstruct注解（兼容处理）
            for attr_name in dir(bean_class):
                if attr_name.startswith('__'):
                    continue

                attr = getattr(bean_class, attr_name)
                if not callable(attr):
                    continue

                # 检查新的生命周期注解
                if hasattr(attr, '__harmony_lifecycle__'):
                    lifecycle_callback = getattr(attr, '__harmony_lifecycle__')
                    if lifecycle_callback.phase == LifecyclePhase.INITIALIZATION:
                        try:
                            method = getattr(instance, attr_name)
                            method()
                        except Exception as e:
                            self.logger.warning(f"Failed to execute @PostConstruct method {attr_name}: {e}")

                # 检查兼容版本注解
                elif hasattr(attr, '__harmony_post_construct__'):
                    try:
                        method = getattr(instance, attr_name)
                        method()
                    except Exception as e:
                        self.logger.warning(f"Failed to execute @PostConstruct method {attr_name}: {e}")

    def _get_bean_name_for_instance(self, instance: Any) -> Optional[str]:
        """获取实例对应的Bean名称"""
        # 首先检查实例是否存储了Bean名称
        if hasattr(instance, '__harmony_bean_name__'):
            return getattr(instance, '__harmony_bean_name__')

        # 通过类型和实例匹配查找Bean名称
        instance_type = type(instance)
        if instance_type in self.type_to_bean_names:
            candidate_names = self.type_to_bean_names[instance_type]
            for bean_name in candidate_names:
                if bean_name in self.singleton_instances:
                    if self.singleton_instances[bean_name] is instance:
                        return bean_name
                else:
                    # 对于原型作用域，返回第一个匹配的名称
                    return bean_name

        return None

    def _resolve_constructor_dependencies(self, definition: BeanDefinition) -> List[Any]:
        """解析构造器依赖"""
        dependencies = []

        for arg in definition.constructor_args:
            # 检查是否为基础数据类型 - 如果是，使用默认值
            if arg.param_type in (bool, str, int, float, dict, list):
                dependencies.append(arg.default_value)
                continue

            if arg.qualifier:
                # 使用限定符查找
                dep = self.get_bean(arg.qualifier)
            else:
                # 使用类型查找
                dep = self.get_bean_by_type(arg.param_type)

            dependencies.append(dep)

        return dependencies

    def _inject_setter_dependencies(self, instance: Any, definition: BeanDefinition) -> None:
        """注入setter依赖"""
        for dep in definition.setter_dependencies:
            try:
                if dep.qualifier:
                    dependency = self.get_bean(dep.qualifier)
                else:
                    dependency = self.get_bean_by_type(dep.dependency_type)

                # 调用setter方法
                setter_name = f"set_{dep.name[0].upper()}{dep.name[1:]}"  # 首字母大写
                if hasattr(instance, setter_name):
                    setter_method = getattr(instance, setter_name)
                    setter_method(dependency)
                else:
                    self.logger.warning(f"Setter method {setter_name} not found on {type(instance)}")

            except Exception as e:
                if dep.required:
                    raise DependencyInjectionException(
                        f"Failed to inject setter dependency '{dep.name}' for {definition.bean_name}: {e}"
                    )
                else:
                    self.logger.debug(f"Optional setter dependency '{dep.name}' not found for {definition.bean_name}")

    def _enhance_bean_definition_from_reflection(self, definition: BeanDefinition) -> None:
        """通过反射增强Bean定义"""
        bean_class = definition.bean_type

        # 如果没有构造器参数定义，自动解析构造器
        if not definition.constructor_args:
            self._parse_constructor_parameters(bean_class, definition)

    def _parse_constructor_parameters(self, bean_class: Type, definition: BeanDefinition) -> None:
        """解析构造器参数"""
        try:
            init_signature = inspect.signature(bean_class.__init__)

            for param_name, param in init_signature.parameters.items():
                if param_name == 'self':
                    continue

                # 跳过 *args 和 **kwargs
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue

                param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
                required = param.default == inspect.Parameter.empty

                definition.add_constructor_arg(
                    name=param_name,
                    param_type=param_type,
                    required=required,
                    default_value=param.default if not required else None
                )

        except Exception as e:
            self.logger.debug(f"Failed to parse constructor for {bean_class.__name__}: {e}")

    def _inject_autowired_fields(self, instance: Any, definition: BeanDefinition):
        """注入autowired标记的字段"""
        bean_class = definition.bean_type

        # 检查类是否有autowired字段
        if hasattr(bean_class, '__harmony_autowired_fields__'):
            autowired_fields = bean_class.__harmony_autowired_fields__

            for field_name, bean_name in autowired_fields.items():
                try:
                    bean_instance = self.get_bean(bean_name)
                    setattr(instance, field_name, bean_instance)
                except NoSuchBeanDefinitionException:
                    raise DependencyInjectionException(
                        f"Could not autowire field '{field_name}' with bean '{bean_name}'"
                    )

    def contains_bean(self, bean_name: str) -> bool:
        """检查是否包含指定名称的Bean"""
        return bean_name in self.bean_definitions

    def get_bean_names(self) -> List[str]:
        """获取所有Bean名称"""
        return list(self.bean_definitions.keys())

    def destroy_singletons(self):
        """销毁所有单例Bean"""
        for bean_name, instance in self.singleton_instances.items():
            definition = self.bean_definitions.get(bean_name)
            if definition and definition.destroy_method:
                try:
                    destroy_method = getattr(instance, definition.destroy_method)
                    destroy_method()
                except (AttributeError, TypeError) as e:
                    # 忽略销毁过程中的异常
                    self.logger.debug(f"Failed to destroy bean {bean_name}: {e}")

        self.singleton_instances.clear()

    def _find_subclass_candidates(self, bean_type: Type) -> List[str]:
        """查找子类候选者"""
        candidates = []
        for registered_type, bean_names in self.type_to_bean_names.items():
            try:
                if issubclass(registered_type, bean_type) and registered_type != bean_type:
                    candidates.extend(bean_names)
            except TypeError:
                # 如果类型不兼容，跳过
                continue
        return candidates

    def get_bean_names_for_type(self, bean_type: Type) -> List[str]:
        """通过类型获取Bean名称列表"""
        names = self.type_to_bean_names.get(bean_type, [])
        # 添加子类
        subclass_names = self._find_subclass_candidates(bean_type)
        return list(set(names + subclass_names))

    def pre_instantiate_singletons(self) -> None:
        """预实例化所有非延迟的单例Bean"""
        for name, definition in self.bean_definitions.items():
            if (definition.scope == ScopeType.SINGLETON and
                    not definition.lazy and
                    name not in self.singleton_instances):
                try:
                    self.logger.debug(f"Pre-instantiating singleton bean: {name}")
                    self.get_bean(name)
                except Exception as e:
                    self.logger.error(f"Failed to pre-instantiate bean {name}: {e}")

    def get_bean_count(self) -> int:
        """获取已注册的Bean数量"""
        return len(self.bean_definitions)

    def is_singleton(self, bean_name: str) -> bool:
        """检查Bean是否为单例"""
        if bean_name not in self.bean_definitions:
            raise NoSuchBeanDefinitionException(bean_name)
        return self.bean_definitions[bean_name].scope == ScopeType.SINGLETON

    def _cleanup_destroyed_prototypes(self):
        """清理已销毁的弱引用"""
        self.prototype_instances = [
            ref for ref in self.prototype_instances
            if ref() is not None
        ]
        self._cleanup_counter = 0

    def _should_cleanup_prototypes(self):
        """检查是否需要清理原型实例"""
        self._cleanup_counter += 1
        return self._cleanup_counter >= self._cleanup_threshold

    def get_prototype_instance_count(self) -> int:
        """获取活跃的原型实例数量"""
        # 先执行清理，确保计数准确
        if self._should_cleanup_prototypes():
            self._cleanup_destroyed_prototypes()

        return len(self.prototype_instances)

    def get_memory_stats(self) -> Dict[str, int]:
        """获取内存使用统计"""
        return {
            'singleton_count': len(self.singleton_instances),
            'active_prototype_count': self.get_prototype_instance_count(),
            'bean_definition_count': len(self.bean_definitions),
            'type_mapping_count': len(self.type_to_bean_names)
        }

    def _find_similar_names(self, bean_name: str, available_names: List[str]) -> List[str]:
        """查找相似的Bean名称"""
        if not available_names:
            return []

        # 使用difflib查找相似的名称
        similar_names = difflib.get_close_matches(bean_name, available_names, n=3, cutoff=0.6)

        # 如果没有找到相似的，尝试其他策略
        if not similar_names:
            # 检查是否有首字母大写的版本
            capitalized_name = bean_name[0].upper() + bean_name[1:] if bean_name else ""
            if capitalized_name in available_names:
                similar_names.append(capitalized_name)

            # 检查是否有首字母小写的版本
            lower_name = bean_name[0].lower() + bean_name[1:] if bean_name else ""
            if lower_name in available_names:
                similar_names.append(lower_name)

        return similar_names

    def _create_instance(self, bean_type: Type, args: List[Any] = None) -> Any:
        """创建实例，处理带注解的类"""
        try:
            # 如果是带注解的类，需要特殊处理
            if hasattr(bean_type, '__harmony_component__') or hasattr(bean_type, '__harmony_service__') or hasattr(bean_type, '__harmony_repository__') or hasattr(bean_type, '__harmony_controller__'):
                # 对于注解类，尝试直接创建
                if args:
                    return bean_type(*args)
                else:
                    return bean_type()
            else:
                # 普通类正常创建
                if args:
                    return bean_type(*args)
                else:
                    return bean_type()
        except Exception as e:
            # 如果创建失败，尝试获取原始类
            if hasattr(bean_type, '__wrapped__'):
                return self._create_instance(bean_type.__wrapped__, args)
            else:
                raise e

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        reflection_stats = reflection_cache.get_cache_stats()
        pool_stats = prototype_object_pool.get_all_statistics()

        return {
            'bean_count': len(self.bean_definitions),
            'singleton_count': len(self.singleton_instances),
            'active_prototype_count': self.get_prototype_instance_count(),
            'reflection_cache': reflection_stats,
            'object_pools': {str(k): v._asdict() if hasattr(v, '_asdict') else v.__dict__
                             for k, v in pool_stats.items()},
            'memory_stats': self.get_memory_stats()
        }

    def optimize_caches(self):
        """优化缓存性能"""
        # 优化反射缓存
        reflection_cache.optimize_for_current_usage()

        # 清理对象池中的闲置对象
        pool_stats = prototype_object_pool.get_all_statistics()
        if pool_stats:
            prototype_object_pool.cleanup_idle_objects()

    def clear_all_caches(self):
        """清空所有缓存"""
        reflection_cache.clear()
        scan_cache.clear()
        metadata_cache.clear()
        prototype_object_pool.clear_all_pools()

    def get_cache_memory_usage(self) -> Dict[str, int]:
        """获取缓存内存使用情况"""
        reflection_stats = reflection_cache.get_cache_stats()
        scan_stats = scan_cache.get_stats()

        return {
            'reflection_cache_size': reflection_stats['constructor_cache_size'] +
                                     reflection_stats['method_cache_size'] +
                                     reflection_stats['annotation_cache_size'],
            'scan_cache_size': scan_stats.get('cache_size', 0),
            'total_cache_size': reflection_stats['constructor_cache_size'] +
                                reflection_stats['method_cache_size'] +
                                reflection_stats['annotation_cache_size'] +
                                scan_stats.get('cache_size', 0)
        }
