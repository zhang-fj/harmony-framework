"""配置类注解 - 增强版本"""

from typing import Type, Dict, Any, List, Optional, Callable
from functools import wraps
import inspect

from ..core.bean_definition import BeanDefinition
from ..container.scope import ScopeType
from ..exceptions.harmony_exceptions import BeanCreationException


def configuration(prefix: str = "", scan_base_packages: Optional[List[str]] = None):
    """
    配置类注解 - 增强版本

    Args:
        prefix: 配置前缀，如 "app.database"
        scan_base_packages: 要扫描的基础包列表
    """

    def decorator(cls):
        config_metadata = {
            'prefix': prefix,
            'properties': {},
            'scan_base_packages': scan_base_packages or []
        }
        cls.__harmony_configuration__ = config_metadata

        # 自动为配置类添加@Component注解
        from ..annotations.component import component
        cls = component(f"{cls.__name__.lower()}Config")(cls)

        return cls

    return decorator


def bean(name: Optional[str] = None,
         primary: bool = False,
         scope: ScopeType = ScopeType.SINGLETON,
         lazy: bool = False,
         init_method: Optional[str] = None,
         destroy_method: Optional[str] = None):
    """
    Bean注解 - 用于配置类中定义Bean（增强版本）

    Args:
        name: Bean名称
        primary: 是否为主要Bean
        scope: Bean作用域
        lazy: 是否延迟初始化
        init_method: 初始化方法名
        destroy_method: 销毁方法名
    """

    def decorator(method):
        # 确保方法是可以调用的
        if not callable(method):
            raise ValueError(f"@bean can only be applied to callable methods, got {type(method)}")

        bean_metadata = {
            'name': name or method.__name__,
            'primary': primary,
            'scope': scope,
            'lazy': lazy,
            'init_method': init_method,
            'destroy_method': destroy_method,
            'factory_method': method
        }
        method.__harmony_bean__ = bean_metadata

        # 如果有初始化或销毁方法，添加相应的注解
        if init_method:
            from ..annotations.lifecycle import PostConstruct
            method.__harmony_post_construct__ = True

        if destroy_method:
            from ..annotations.lifecycle import PreDestroy
            method.__harmony_pre_destroy__ = True

        return method

    return decorator


def import_resource(resource_location: str):
    """
    导入资源注解

    Args:
        resource_location: 资源位置
    """

    def decorator(method_or_class):
        resource_metadata = {
            'location': resource_location
        }
        method_or_class.__harmony_import_resource__ = resource_metadata
        return method_or_class

    return decorator


def conditional_on_property(name: str, having_value: Optional[str] = None,
                           match_if_missing: bool = False):
    """
    条件注解 - 基于属性存在条件

    Args:
        name: 属性名
        having_value: 期望的属性值
        match_if_missing: 属性不存在时是否匹配
    """

    def decorator(method_or_class):
        condition_metadata = {
            'type': 'property',
            'name': name,
            'having_value': having_value,
            'match_if_missing': match_if_missing
        }
        method_or_class.__harmony_conditional__ = condition_metadata
        return method_or_class

    return decorator


def conditional_on_class(*classes: Type):
    """
    条件注解 - 基于类存在条件

    Args:
        *classes: 要检查的类
    """

    def decorator(method_or_class):
        condition_metadata = {
            'type': 'class',
            'classes': list(classes)
        }
        method_or_class.__harmony_conditional__ = condition_metadata
        return method_or_class

    return decorator


def lazy(value: bool = True):
    """
    延迟加载注解

    Args:
        value: 是否延迟加载
    """

    def decorator(method_or_class):
        method_or_class.__harmony_lazy__ = value
        return method_or_class

    return decorator


class ConfigurationClassProcessor:
    """配置类处理器 - 用于处理@Configuration类"""

    def __init__(self, bean_factory):
        self.bean_factory = bean_factory
        self.processed_configurations = set()

    def process_configuration_class(self, config_class: Type) -> List[BeanDefinition]:
        """处理配置类，生成Bean定义"""
        if config_class in self.processed_configurations:
            return []

        self.processed_configurations.add(config_class)

        # 检查是否为配置类
        if not hasattr(config_class, '__harmony_configuration__'):
            return []

        config_metadata = getattr(config_class, '__harmony_configuration__')
        bean_definitions = []

        try:
            # 创建配置类实例
            config_instance = self._create_configuration_instance(config_class)

            # 处理配置属性绑定
            self._bind_configuration_properties(config_instance, config_metadata)

            # 处理@Bean方法
            bean_definitions.extend(self._process_bean_methods(config_instance, config_class))

            # 处理@ImportResource注解
            if hasattr(config_class, '__harmony_import_resource__'):
                self._process_import_resources(config_instance, config_class)

        except Exception as e:
            raise BeanCreationException(
                f"Failed to process configuration class {config_class.__name__}: {e}"
            )

        return bean_definitions

    def _create_configuration_instance(self, config_class: Type) -> Any:
        """创建配置类实例"""
        try:
            # 尝试无参构造
            return config_class()
        except TypeError as e:
            # 如果需要参数，尝试从Bean工厂获取
            if hasattr(config_class, '__init__'):
                init_signature = inspect.signature(config_class.__init__)
                init_params = []

                for param_name, param in init_signature.parameters.items():
                    if param_name == 'self':
                        continue

                    # 尝试解析依赖
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else None
                    if param_type:
                        try:
                            dependency = self.bean_factory.get_bean_by_type(param_type)
                            init_params.append(dependency)
                        except Exception:
                            if param.default == inspect.Parameter.empty:
                                raise BeanCreationException(
                                    f"Cannot resolve dependency '{param_name}' for configuration class {config_class.__name__}"
                                )
                            init_params.append(param.default)
                    else:
                        init_params.append(param.default if param.default != inspect.Parameter.empty else None)

                return config_class(*init_params)
            else:
                raise e

    def _bind_configuration_properties(self, config_instance: Any, config_metadata: Dict[str, Any]):
        """绑定配置属性"""
        from .value import PropertyValueResolver
        from .environment import environment_manager

        resolver = PropertyValueResolver(environment_manager.get_all_properties())
        binder = ConfigurationPropertiesBinder(resolver)
        binder.bind_properties(type(config_instance))
        binder.bind_instance_properties(config_instance)

    def _process_bean_methods(self, config_instance: Any, config_class: Type) -> List[BeanDefinition]:
        """处理@Bean方法"""
        bean_definitions = []

        for name, method in inspect.getmembers(config_class, inspect.ismethod):
            if hasattr(method, '__harmony_bean__'):
                bean_metadata = getattr(method, '__harmony_bean__')
                bean_def = self._create_bean_definition_from_method(
                    method, bean_metadata, config_instance
                )
                bean_definitions.append(bean_def)

        return bean_definitions

    def _create_bean_definition_from_method(self, method: Callable,
                                           bean_metadata: Dict[str, Any],
                                           config_instance: Any) -> BeanDefinition:
        """从@Bean方法创建Bean定义"""
        bean_name = bean_metadata['name']
        bean_class = self._infer_return_type(method)

        bean_def = BeanDefinition(
            bean_class=bean_class,
            bean_name=bean_name,
            scope=bean_metadata.get('scope', ScopeType.SINGLETON),
            primary=bean_metadata.get('primary', False),
            lazy=bean_metadata.get('lazy', False),
            init_method=bean_metadata.get('init_method'),
            destroy_method=bean_metadata.get('destroy_method'),
            factory_method=lambda: self._invoke_bean_method(method, config_instance)
        )

        # 解析@Bean方法的依赖
        self._resolve_method_dependencies(method, bean_def)

        return bean_def

    def _infer_return_type(self, method: Callable) -> Type:
        """推断方法的返回类型"""
        # 首先检查类型注解
        if hasattr(method, '__annotations__') and 'return' in method.__annotations__:
            return_type = method.__annotations__['return']
            if return_type != inspect.Signature.empty:
                return return_type

        # 如果没有类型注解，尝试通过方法名推断
        method_name = method.__name__.lower()
        if 'service' in method_name:
            return object  # 通用类型
        elif 'repository' in method_name:
            return object
        elif 'controller' in method_name:
            return object
        else:
            return object

    def _invoke_bean_method(self, method: Callable, config_instance: Any) -> Any:
        """调用@Bean方法创建Bean实例"""
        try:
            return method()
        except Exception as e:
            raise BeanCreationException(
                f"Failed to invoke @Bean method {method.__name__}: {e}"
            )

    def _resolve_method_dependencies(self, method: Callable, bean_def: BeanDefinition):
        """解析@Bean方法的依赖"""
        signature = inspect.signature(method)
        constructor_args = bean_def.constructor_args

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            param_type = param.annotation if param.annotation != inspect.Parameter.empty else object
            required = param.default == inspect.Parameter.empty
            default_value = param.default if not required else None

            bean_def.add_constructor_arg(
                name=param_name,
                param_type=param_type,
                required=required,
                default_value=default_value
            )

    def _process_import_resources(self, config_instance: Any, config_class: Type):
        """处理@ImportResource注解"""
        import_metadata = getattr(config_class, '__harmony_import_resource__')
        resource_location = import_metadata['location']

        # 这里可以添加资源导入逻辑
        # 例如：加载Python文件、YAML文件等
        pass

    def should_process(self, cls: Type) -> bool:
        """检查是否应该处理此类"""
        if not hasattr(cls, '__harmony_configuration__'):
            return False

        # 检查条件注解
        if hasattr(cls, '__harmony_conditional__'):
            condition = getattr(cls, '__harmony_conditional__')
            return self._evaluate_condition(condition)

        return True

    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """评估条件注解"""
        from .environment import environment_manager

        if condition['type'] == 'property':
            prop_name = condition['name']
            having_value = condition.get('having_value')
            match_if_missing = condition.get('match_if_missing', False)

            all_props = environment_manager.get_all_properties()

            if prop_name not in all_props:
                return match_if_missing

            if having_value is not None:
                return str(all_props[prop_name]) == having_value

            return True

        elif condition['type'] == 'class':
            # 检查类是否存在
            for cls in condition['classes']:
                try:
                    import importlib
                    importlib.import_module(cls.__module__)
                except ImportError:
                    return False
            return True

        return True


class ConfigurationPropertiesBinder:
    """配置属性绑定器"""

    def __init__(self, resolver: 'PropertyValueResolver'):
        self.resolver = resolver

    def bind_properties(self, config_class: Type) -> Any:
        """
        绑定配置属性到配置类

        Args:
            config_class: 配置类

        Returns:
            配置类实例
        """
        # 获取配置注解信息
        config_info = getattr(config_class, '__harmony_configuration__', {})
        prefix = config_info.get('prefix', '')

        # 创建配置实例
        config_instance = config_class()

        # 绑定属性
        for attr_name in dir(config_class):
            if not attr_name.startswith('_'):
                attr = getattr(config_class, attr_name)
                if hasattr(attr, '__harmony_value__'):
                    value_info = attr.__harmony_value__
                    expression = value_info['expression']
                    default = value_info['default']
                    required = value_info['required']

                    # 构建完整的配置键
                    if prefix and not expression.startswith('${') and '.' in expression:
                        full_expression = f"{prefix}.{expression}"
                    elif prefix and not expression.startswith('${'):
                        full_expression = f"{prefix}.{expression}"
                    else:
                        full_expression = expression

                    # 解析配置值
                    try:
                        value = self.resolver.resolve_value(full_expression, default, required)
                        setattr(config_instance, attr_name, value)
                    except ValueError as e:
                        if required:
                            raise e

        return config_instance

    def collect_bean_definitions(self, config_instance: Any) -> List[Dict]:
        """
        收集配置类中定义的Bean

        Args:
            config_instance: 配置类实例

        Returns:
            Bean定义列表
        """
        bean_definitions = []

        for attr_name in dir(config_instance):
            if not attr_name.startswith('_'):
                attr = getattr(config_instance, attr_name)
                if callable(attr) and hasattr(attr, '__harmony_bean__'):
                    bean_info = attr.__harmony_bean__
                    bean_definitions.append({
                        'method': attr,
                        'name': bean_info['name'],
                        'primary': bean_info['primary'],
                        'factory': config_instance
                    })

        return bean_definitions

    def bind_instance_properties(self, instance: Any):
        """
        绑定配置属性到实例

        Args:
            instance: 要绑定属性的实例
        """
        config_class = type(instance)
        config_info = getattr(config_class, '__harmony_configuration__', {})
        prefix = config_info.get('prefix', '')

        # 为实例属性绑定配置值
        for attr_name in dir(instance):
            if not attr_name.startswith('_'):
                attr = getattr(config_class, attr_name)
                if hasattr(attr, '__harmony_value__'):
                    value_info = attr.__harmony_value__
                    expression = value_info['expression']
                    default = value_info['default']
                    required = value_info['required']

                    # 构建完整的配置键
                    if prefix and not expression.startswith('${') and '.' in expression:
                        full_expression = f"{prefix}.{expression}"
                    elif prefix and not expression.startswith('${'):
                        full_expression = f"{prefix}.{expression}"
                    else:
                        full_expression = expression

                    # 解析配置值
                    try:
                        value = self.resolver.resolve_value(full_expression, default, required)
                        setattr(instance, attr_name, value)
                    except ValueError as e:
                        if required:
                            raise e


# 全局配置类处理器实例
_configuration_processor = None


def get_configuration_processor(bean_factory=None):
    """获取配置类处理器实例"""
    global _configuration_processor
    if _configuration_processor is None and bean_factory is not None:
        _configuration_processor = ConfigurationClassProcessor(bean_factory)
    return _configuration_processor


def process_configuration_classes(bean_factory, classes: List[Type]) -> List[BeanDefinition]:
    """处理多个配置类"""
    processor = get_configuration_processor(bean_factory)
    all_definitions = []

    for config_class in classes:
        if processor.should_process(config_class):
            definitions = processor.process_configuration_class(config_class)
            all_definitions.extend(definitions)

    return all_definitions
