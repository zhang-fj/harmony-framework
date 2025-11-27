"""
智能依赖注入处理器 - 统一处理各种注入方式
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from ..core.bean_definition import BeanDefinition
from ..exceptions.harmony_exceptions import DependencyInjectionException
from ..extensions.reflection_cache import reflection_cache

try:
    from ..utils.logger import get_logger
except ImportError:
    import logging


    def get_logger(name):
        return logging.getLogger(name)


class InjectionType(Enum):
    """注入类型枚举"""
    CONSTRUCTOR = "constructor"
    FIELD = "field"
    SETTER = "setter"
    METHOD = "method"


@dataclass
class InjectionPoint:
    """注入点信息"""
    injection_type: InjectionType
    name: str
    target_type: Type
    required: bool = True
    qualifier: Optional[str] = None
    default_value: Any = None
    setter_method: Optional[str] = None


class InjectionProcessor:
    """智能依赖注入处理器"""

    def __init__(self, bean_factory):
        self.bean_factory = bean_factory
        self.logger = get_logger('injection_processor')
        self._injection_cache = {}

    def process_injection(self, instance: Any, definition: BeanDefinition) -> None:
        """统一的依赖注入入口"""
        injection_points = self._collect_injection_points(definition)

        for injection_point in injection_points:
            try:
                dependency = self._resolve_dependency(injection_point)
                self._inject_dependency(instance, injection_point, dependency)
            except Exception as e:
                if injection_point.required:
                    raise DependencyInjectionException(
                        f"Failed to inject dependency '{injection_point.name}' "
                        f"of type {injection_point.target_type}: {e}",
                        dependency_name=injection_point.name,
                        cause=e
                    )
                else:
                    self.logger.debug(f"Optional dependency '{injection_point.name}' not injected: {e}")

    def _collect_injection_points(self, definition: BeanDefinition) -> List[InjectionPoint]:
        """收集所有注入点"""
        cache_key = f"{definition.bean_name}_{id(definition)}"
        if cache_key in self._injection_cache:
            return self._injection_cache[cache_key]

        injection_points = []

        # 收集构造器注入点
        injection_points.extend(self._collect_constructor_injection_points(definition))

        # 收集字段注入点
        injection_points.extend(self._collect_field_injection_points(definition))

        # 收集Setter注入点
        injection_points.extend(self._collect_setter_injection_points(definition))

        # 缓存结果
        self._injection_cache[cache_key] = injection_points
        return injection_points

    def _collect_constructor_injection_points(self, definition: BeanDefinition) -> List[InjectionPoint]:
        """收集构造器注入点"""
        injection_points = []
        bean_class = definition.bean_type

        # 使用反射缓存获取构造器信息
        constructor_info = reflection_cache.get_constructor_info(bean_class)

        for param_name, param_type, required, default_value in constructor_info.parameters:
            # 检查是否为基础数据类型
            if param_type in (bool, str, int, float, dict, list):
                continue

            # 查找对应的构造器参数定义
            qualifier = None
            for arg in definition.constructor_args:
                if arg.name == param_name:
                    qualifier = arg.qualifier
                    break

            injection_point = InjectionPoint(
                injection_type=InjectionType.CONSTRUCTOR,
                name=param_name,
                target_type=param_type,
                required=required,
                qualifier=qualifier,
                default_value=default_value
            )
            injection_points.append(injection_point)

        return injection_points

    def _collect_field_injection_points(self, definition: BeanDefinition) -> List[InjectionPoint]:
        """收集字段注入点"""
        injection_points = []
        bean_class = definition.bean_type

        # 检查类的autowired字段
        if hasattr(bean_class, '__harmony_autowired_fields__'):
            autowired_fields = bean_class.__harmony_autowired_fields__

            for field_name, bean_name in autowired_fields.items():
                injection_point = InjectionPoint(
                    injection_type=InjectionType.FIELD,
                    name=field_name,
                    target_type=self._infer_field_type(bean_class, field_name),
                    required=True,
                    qualifier=bean_name
                )
                injection_points.append(injection_point)

        return injection_points

    def _collect_setter_injection_points(self, definition: BeanDefinition) -> List[InjectionPoint]:
        """收集Setter注入点"""
        injection_points = []

        for dep_def in definition.setter_dependencies:
            injection_point = InjectionPoint(
                injection_type=InjectionType.SETTER,
                name=dep_def.name,
                target_type=dep_def.dependency_type,
                required=dep_def.required,
                qualifier=dep_def.qualifier,
                setter_method=f"set_{dep_def.name[0].upper()}{dep_def.name[1:]}"
            )
            injection_points.append(injection_point)

        return injection_points

    def _resolve_dependency(self, injection_point: InjectionPoint) -> Any:
        """解析依赖"""
        try:
            if injection_point.qualifier:
                return self.bean_factory.get_bean(injection_point.qualifier)
            else:
                return self.bean_factory.get_bean_by_type(injection_point.target_type)
        except Exception as e:
            if injection_point.default_value is not None:
                return injection_point.default_value
            raise e

    def _inject_dependency(self, instance: Any, injection_point: InjectionPoint, dependency: Any) -> None:
        """执行依赖注入"""
        if injection_point.injection_type == InjectionType.FIELD:
            setattr(instance, injection_point.name, dependency)
        elif injection_point.injection_type == InjectionType.SETTER:
            if hasattr(instance, injection_point.setter_method):
                setter_method = getattr(instance, injection_point.setter_method)
                setter_method(dependency)
            else:
                raise DependencyInjectionException(f"Setter method {injection_point.setter_method} not found")
        elif injection_point.injection_type == InjectionType.CONSTRUCTOR:
            # 构造器注入在实例创建时处理，这里不需要做任何事
            pass

    def _infer_field_type(self, bean_class: Type, field_name: str) -> Type:
        """推断字段类型"""
        # 使用反射缓存获取字段信息
        annotations = reflection_cache.get_annotations(bean_class)

        # 检查类型注解
        if hasattr(bean_class, '__annotations__') and field_name in bean_class.__annotations__:
            return bean_class.__annotations__[field_name]

        # 默认返回object类型
        return object

    def validate_dependencies(self, definition: BeanDefinition) -> List[str]:
        """验证依赖是否可以解析"""
        errors = []
        injection_points = self._collect_injection_points(definition)

        for injection_point in injection_points:
            if injection_point.required:
                try:
                    self._resolve_dependency(injection_point)
                except Exception as e:
                    errors.append(
                        f"Required dependency '{injection_point.name}' "
                        f"of type {injection_point.target_type} cannot be resolved: {e}"
                    )

        return errors

    def get_dependency_graph(self, bean_name: str, visited: Optional[set] = None) -> Dict[str, Any]:
        """获取依赖关系图"""
        if visited is None:
            visited = set()

        if bean_name in visited:
            return {"circular": True}

        visited.add(bean_name)

        try:
            definition = self.bean_factory.bean_definitions[bean_name]
            injection_points = self._collect_injection_points(definition)

            dependencies = {}
            for injection_point in injection_points:
                dep_name = injection_point.qualifier or str(injection_point.target_type)
                dependencies[dep_name] = self.get_dependency_graph(dep_name, visited.copy())

            return dependencies

        except Exception as e:
            return {"error": str(e)}

    def optimize_injection_order(self, bean_definitions: Dict[str, BeanDefinition]) -> List[str]:
        """优化Bean创建顺序以减少重试"""
        # 构建依赖图
        dependency_graph = {}
        for bean_name, definition in bean_definitions.items():
            injection_points = self._collect_injection_points(definition)
            dependencies = []

            for injection_point in injection_points:
                if injection_point.qualifier:
                    dependencies.append(injection_point.qualifier)
                else:
                    # 对于类型依赖，使用第一个匹配的Bean
                    matching_beans = self.bean_factory.get_bean_names_for_type(injection_point.target_type)
                    if matching_beans:
                        dependencies.append(matching_beans[0])

            dependency_graph[bean_name] = dependencies

        # 拓扑排序
        return self._topological_sort(dependency_graph)

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        in_degree = {node: 0 for node in graph}

        # 计算入度
        for node in graph:
            for dependency in graph[node]:
                if dependency in in_degree:
                    in_degree[dependency] += 1

        # 找到所有入度为0的节点
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # 更新依赖该节点的其他节点的入度
            for dependency in graph.get(node, []):
                if dependency in in_degree:
                    in_degree[dependency] -= 1
                    if in_degree[dependency] == 0:
                        queue.append(dependency)

        return result

    def clear_cache(self):
        """清空注入缓存"""
        self._injection_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            'injection_cache_size': len(self._injection_cache)
        }


class AutoInjectionProcessor:
    """自动注入处理器 - 智能推断注入点"""

    def __init__(self, injection_processor: InjectionProcessor):
        self.injection_processor = injection_processor
        self.logger = get_logger('auto_injection_processor')

    def auto_configure_injection(self, instance: Any, bean_class: Type) -> None:
        """自动配置依赖注入"""
        # 扫描类的所有成员
        for attr_name in dir(bean_class):
            if attr_name.startswith('_'):
                continue

            attr = getattr(bean_class, attr_name)

            # 检查是否为需要注入的依赖
            if self._is_dependency_candidate(attr, attr_name):
                injection_point = self._create_injection_point(bean_class, attr_name, attr)
                if injection_point:
                    try:
                        dependency = self.injection_processor._resolve_dependency(injection_point)
                        self.injection_processor._inject_dependency(instance, injection_point, dependency)
                    except Exception as e:
                        self.logger.debug(f"Auto injection failed for {attr_name}: {e}")

    def _is_dependency_candidate(self, attr: Any, attr_name: str) -> bool:
        """检查是否为依赖候选"""
        # 检查类型注解
        if hasattr(attr, '__annotations__') and attr_name in attr.__annotations__:
            annotation = attr.__annotations__[attr_name]
            # 如果是自定义类型（非基础类型），则认为是依赖候选
            return self._is_custom_type(annotation)

        return False

    def _is_custom_type(self, type_hint: Type) -> bool:
        """检查是否为自定义类型"""
        # 基础类型列表
        basic_types = (str, int, float, bool, list, dict, tuple, set, bytes, bytearray)
        return not (type_hint in basic_types or
                    hasattr(type_hint, '__module__') and type_hint.__module__ in ('builtins', 'typing'))

    def _create_injection_point(self, bean_class: Type, attr_name: str, attr: Any) -> Optional[InjectionPoint]:
        """创建注入点"""
        # 获取类型注解
        if hasattr(bean_class, '__annotations__') and attr_name in bean_class.__annotations__:
            target_type = bean_class.__annotations__[attr_name]

            # 尝试根据类型推断Bean名称
            bean_name = self._infer_bean_name(target_type, attr_name)

            return InjectionPoint(
                injection_type=InjectionType.FIELD,
                name=attr_name,
                target_type=target_type,
                required=True,
                qualifier=bean_name
            )

        return None

    def _infer_bean_name(self, target_type: Type, field_name: str) -> Optional[str]:
        """推断Bean名称"""
        # 1. 尝试使用类名首字母小写
        type_name = target_type.__name__
        inferred_name = type_name[0].lower() + type_name[1:] if type_name else field_name

        # 2. 检查是否存在对应的Bean
        if self.injection_processor.bean_factory.contains_bean(inferred_name):
            return inferred_name

        # 3. 检查是否按类型能找到Bean
        try:
            bean_names = self.injection_processor.bean_factory.get_bean_names_for_type(target_type)
            if bean_names:
                return bean_names[0]  # 返回第一个匹配的
        except:
            pass

        # 4. 使用字段名作为Bean名称
        if self.injection_processor.bean_factory.contains_bean(field_name):
            return field_name

        return None
