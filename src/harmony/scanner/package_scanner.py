import importlib
import inspect
import pkgutil
from typing import Type

from ..core.application_context import ApplicationContext
from ..core.bean_definition import BeanDefinition
from ..core.scope import ScopeType


class PackageScanner:
    """包扫描器"""

    def __init__(self, context: ApplicationContext):
        self.context = context

    def scan_package(self, package_name: str):
        """扫描指定包"""
        try:
            package = importlib.import_module(package_name)
            self._process_module(package)

            # 递归扫描子包
            for _, name, is_pkg in pkgutil.iter_modules(package.__path__):
                if is_pkg:
                    self.scan_package(f"{package_name}.{name}")
                else:
                    module = importlib.import_module(f"{package_name}.{name}")
                    self._process_module(module)

        except ImportError as e:
            print(f"Warning: Could not import package {package_name}: {e}")

    def _process_module(self, module):
        """处理模块中的类"""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if self._is_component_class(obj):
                self._register_component(obj)

    def _is_component_class(self, cls: Type) -> bool:
        """检查类是否是组件类"""
        return (hasattr(cls, '__harmony_component__') and
                cls.__harmony_component__ is True)

    def _register_component(self, cls: Type):
        """注册组件类"""
        bean_name = getattr(cls, '__harmony_bean_name__', cls.__name__)
        scope = getattr(cls, '__harmony_scope__', ScopeType.SINGLETON)

        definition = BeanDefinition(
            bean_type=cls,
            bean_name=bean_name,
            scope=scope
        )

        # 处理生命周期方法
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, '__harmony_post_construct__'):
                definition.init_method = method_name
            elif hasattr(method, '__harmony_pre_destroy__'):
                definition.destroy_method = method_name

        self.context.bean_factory.register_bean_definition(definition)
