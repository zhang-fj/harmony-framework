"""
Bean创建器 - 专门负责Bean实例的创建逻辑
"""

from typing import Any

from ..core.bean_definition import BeanDefinition
from ..exceptions.harmony_exceptions import BeanCreationException, DependencyInjectionException

try:
    from ..utils.logger import get_logger
except ImportError:
    import logging


    def get_logger(name):
        return logging.getLogger(name)


class BeanCreator:
    """Bean创建器 - 负责Bean实例的创建和初始化"""

    def __init__(self, dependency_resolver, lifecycle_manager):
        self.dependency_resolver = dependency_resolver
        self.lifecycle_manager = lifecycle_manager
        self.logger = get_logger('bean_creator')

    def create_bean_instance(self, definition: BeanDefinition) -> Any:
        """
        创建Bean实例

        Args:
            definition: Bean定义

        Returns:
            创建的Bean实例
        """
        try:
            instance = self._instantiate_bean(definition)
            self._perform_dependency_injection(instance, definition)
            self._invoke_initialization_methods(instance, definition)

            self.logger.debug(f"Successfully created bean instance: {definition.bean_name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create bean {definition.bean_name}: {e}")
            raise BeanCreationException(
                definition.bean_name,
                str(e),
                cause=e,
                bean_type=definition.bean_type
            )

    def _instantiate_bean(self, definition: BeanDefinition) -> Any:
        """实例化Bean"""
        if definition.factory_method:
            return definition.factory_method()

        if definition.constructor_args:
            constructor_deps = self.dependency_resolver.resolve_constructor_dependencies(definition)
            return definition.bean_type(*constructor_deps)

        return definition.bean_type()

    def _perform_dependency_injection(self, instance: Any, definition: BeanDefinition) -> None:
        """执行依赖注入"""
        # 字段注入
        self._inject_autowired_fields(instance, definition)

        # Setter注入
        self._inject_setter_dependencies(instance, definition)

    def _inject_autowired_fields(self, instance: Any, definition: BeanDefinition) -> None:
        """注入autowired标记的字段"""
        bean_class = definition.bean_type

        if hasattr(bean_class, '__harmony_autowired_fields__'):
            autowired_fields = bean_class.__harmony_autowired_fields__

            for field_name, bean_name in autowired_fields.items():
                try:
                    bean_instance = self.dependency_resolver.get_bean_by_name(bean_name)
                    setattr(instance, field_name, bean_instance)
                except Exception as e:
                    raise DependencyInjectionException(
                        f"Could not autowire field '{field_name}' with bean '{bean_name}': {e}",
                        dependency_name=field_name,
                        bean_name=definition.bean_name,
                        cause=e
                    )

    def _inject_setter_dependencies(self, instance: Any, definition: BeanDefinition) -> None:
        """注入setter依赖"""
        for dep in definition.setter_dependencies:
            try:
                dependency = self.dependency_resolver.resolve_dependency(dep)
                setter_name = f"set_{dep.name[0].upper()}{dep.name[1:]}"

                if hasattr(instance, setter_name):
                    setter_method = getattr(instance, setter_name)
                    setter_method(dependency)
                else:
                    self.logger.warning(f"Setter method {setter_name} not found on {type(instance)}")

            except Exception as e:
                if dep.required:
                    raise DependencyInjectionException(
                        f"Failed to inject setter dependency '{dep.name}' for {definition.bean_name}: {e}",
                        dependency_name=dep.name,
                        bean_name=definition.bean_name,
                        cause=e
                    )
                else:
                    self.logger.debug(f"Optional setter dependency '{dep.name}' not found for {definition.bean_name}")

    def _invoke_initialization_methods(self, instance: Any, definition: BeanDefinition) -> None:
        """调用初始化方法"""
        # 调用自定义初始化方法
        if definition.init_method:
            init_method = getattr(instance, definition.init_method)
            init_method()

        # 调用PostConstruct方法
        self._invoke_post_construct_methods(instance)

    def _invoke_post_construct_methods(self, instance: Any) -> None:
        """调用PostConstruct方法"""
        # 检查__post_construct__方法（兼容性）
        if hasattr(instance, '__post_construct__'):
            instance.__post_construct__()
            return

        # 检查新版本的PostConstruct注解
        bean_class = instance.__class__
        for attr_name in dir(bean_class):
            if not attr_name.startswith('__'):
                attr = getattr(bean_class, attr_name)
                if (hasattr(attr, '__harmony_post_construct__') or
                        hasattr(attr, '__harmony_lifecycle__')):
                    try:
                        method = getattr(instance, attr_name)
                        method()
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to invoke PostConstruct method {attr_name}: {e}")
                        pass
