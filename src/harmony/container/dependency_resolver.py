"""
依赖解析器 - 专门负责Bean依赖的解析
"""

from typing import Any, List, Optional

from ..core.bean_definition import BeanDefinition, DependencyDefinition
from ..exceptions.harmony_exceptions import (
    NoSuchBeanDefinitionException,
    DependencyInjectionException
)

try:
    from ..utils.logger import get_logger
except ImportError:
    import logging


    def get_logger(name):
        return logging.getLogger(name)


class DependencyResolver:
    """依赖解析器 - 负责解析和注入Bean依赖"""

    def __init__(self, bean_factory):
        self.bean_factory = bean_factory
        self.logger = get_logger('dependency_resolver')

    def resolve_constructor_dependencies(self, definition: BeanDefinition) -> List[Any]:
        """
        解析构造器依赖

        Args:
            definition: Bean定义

        Returns:
            解析后的依赖实例列表
        """
        dependencies = []

        for arg in definition.constructor_args:
            # 检查是否为基础数据类型
            if arg.param_type in (bool, str, int, float, dict, list):
                dependencies.append(arg.default_value)
                continue

            dependency = self._resolve_single_dependency(arg.param_type, arg.qualifier, arg.default_value)
            dependencies.append(dependency)

        return dependencies

    def resolve_dependency(self, dep_def: DependencyDefinition) -> Any:
        """
        解析单个依赖

        Args:
            dep_def: 依赖定义

        Returns:
            依赖实例
        """
        return self._resolve_single_dependency(dep_def.dependency_type, dep_def.qualifier)

    def _resolve_single_dependency(self, dependency_type: type, qualifier: Optional[str] = None,
                                   default_value: Any = None) -> Any:
        """解析单个依赖的内部方法"""
        try:
            if qualifier:
                return self.bean_factory.get_bean(qualifier)
            else:
                return self.bean_factory.get_bean_by_type(dependency_type)
        except NoSuchBeanDefinitionException as e:
            if default_value is not None:
                return default_value
            raise DependencyInjectionException(
                f"Could not resolve dependency of type {dependency_type}: {e}",
                dependency_name=qualifier or str(dependency_type),
                cause=e
            )

    def get_bean_by_name(self, bean_name: str) -> Any:
        """通过名称获取Bean（委托给BeanFactory）"""
        return self.bean_factory.get_bean(bean_name)

    def validate_dependencies(self, definition: BeanDefinition) -> List[str]:
        """
        验证Bean的依赖是否可以解析

        Args:
            definition: Bean定义

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 验证构造器依赖
        for arg in definition.constructor_args:
            if arg.param_type not in (bool, str, int, float, dict, list):  # 非基础类型
                if not self._can_resolve_dependency(arg.param_type, arg.qualifier):
                    if arg.required:
                        errors.append(
                            f"Required constructor dependency '{arg.name}' of type {arg.param_type} cannot be resolved")

        # 验证字段依赖
        for dep in definition.field_dependencies:
            if not self._can_resolve_dependency(dep.dependency_type, dep.qualifier):
                if dep.required:
                    errors.append(
                        f"Required field dependency '{dep.name}' of type {dep.dependency_type} cannot be resolved")

        # 验证setter依赖
        for dep in definition.setter_dependencies:
            if not self._can_resolve_dependency(dep.dependency_type, dep.qualifier):
                if dep.required:
                    errors.append(
                        f"Required setter dependency '{dep.name}' of type {dep.dependency_type} cannot be resolved")

        return errors

    def _can_resolve_dependency(self, dependency_type: type, qualifier: Optional[str] = None) -> bool:
        """检查依赖是否可以解析"""
        try:
            if qualifier:
                return self.bean_factory.contains_bean(qualifier)
            else:
                # 尝试按类型解析，但不实际创建Bean
                candidate_names = self.bean_factory.get_bean_names_for_type(dependency_type)
                return len(candidate_names) > 0
        except Exception:
            return False

    def get_dependency_graph(self, bean_name: str, visited: Optional[set] = None) -> dict:
        """
        获取Bean的依赖图

        Args:
            bean_name: Bean名称
            visited: 已访问的Bean集合（用于避免循环）

        Returns:
            依赖图字典
        """
        if visited is None:
            visited = set()

        if bean_name in visited:
            return {"circular": True}

        visited.add(bean_name)

        try:
            definition = self.bean_factory.bean_definitions[bean_name]
            dependencies = {}

            # 构造器依赖
            for arg in definition.constructor_args:
                if arg.param_type not in (bool, str, int, float, dict, list):
                    dep_name = arg.qualifier or str(arg.param_type)
                    dependencies[dep_name] = self.get_dependency_graph(dep_name, visited.copy())

            # 字段依赖
            for dep in definition.field_dependencies:
                dep_name = dep.qualifier or str(dep.dependency_type)
                dependencies[dep_name] = self.get_dependency_graph(dep_name, visited.copy())

            # Setter依赖
            for dep in definition.setter_dependencies:
                dep_name = dep.qualifier or str(dep.dependency_type)
                dependencies[dep_name] = self.get_dependency_graph(dep_name, visited.copy())

            return dependencies

        except Exception as e:
            return {"error": str(e)}
