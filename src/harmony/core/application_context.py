from typing import List, Optional, Type, Any

from .bean_definition import BeanDefinition
from .bean_factory import BeanFactory
from ..config.configuration import ConfigurationPropertiesBinder
from ..config.value import PropertyValueResolver
from ..container.scope import ScopeType
from ..scanner import ComponentScanner


class ApplicationContext:
    """应用上下文 - 核心IoC容器 - 增强版"""

    def __init__(self):
        self.bean_factory = BeanFactory()
        self.scanner = ComponentScanner()
        self.scan_packages = []  # 要扫描的包
        self.scan_classes = []  # 要扫描的类
        self.value_resolver = PropertyValueResolver()
        self.config_binder = ConfigurationPropertiesBinder(self.value_resolver)

    def register_bean(
            self,
            bean_type: Type,
            bean_name: Optional[str] = None,
            scope: str = ScopeType.SINGLETON.value,
            constructor_args: List[Any] = None,
            primary: bool = False,
            lazy: bool = False
    ):
        # 处理带注解的类 - 如果bean_type是装饰器函数，需要获取原始类
        actual_bean_type = self._extract_original_class(bean_type)

        # 使用提供的bean_name或类名
        actual_bean_name = bean_name or actual_bean_type.__name__
        scope_enum = ScopeType(scope.lower())

        definition = BeanDefinition(
            bean_type=actual_bean_type,
            bean_name=actual_bean_name,
            scope=scope_enum,
            primary=primary,
            lazy=lazy
        )

        # 添加构造器参数
        if constructor_args:
            for arg in constructor_args:
                definition.add_constructor_arg(type(arg), arg)

        self.bean_factory.register_bean_definition(definition)

    def _extract_original_class(self, bean_type):
        """从装饰器函数中提取原始类"""
        # 如果是函数而不是类，并且具有组件注解标记
        if callable(bean_type) and not isinstance(bean_type, type):
            # 尝试获取闭包中的原始类
            if hasattr(bean_type, '__closure__') and bean_type.__closure__:
                for closure_cell in bean_type.__closure__:
                    if isinstance(closure_cell.cell_contents, type):
                        return closure_cell.cell_contents
            # 如果找不到，尝试从__globals__获取
            if hasattr(bean_type, '__globals__'):
                # 寻找最近的类定义
                for name, obj in bean_type.__globals__.items():
                    if isinstance(obj, type) and hasattr(obj, '__harmony_component__'):
                        return obj
        return bean_type

    def get_bean(self, bean_name: str) -> Any:
        """根据名称获取Bean实例"""
        return self.bean_factory.get_bean(bean_name)

    def contains_bean(self, bean_name: str) -> bool:
        """检查是否包含指定名称的Bean"""
        return self.bean_factory.contains_bean(bean_name)

    def get_bean_names(self) -> List[str]:
        """获取所有Bean名称"""
        return self.bean_factory.get_bean_names()

    # 增强的组件扫描功能
    def component_scan(self, *base_packages: str, exclude_patterns: List[str] = None,
                       include_patterns: List[str] = None, filters: List[callable] = None):
        """
        组件扫描配置

        Args:
            *base_packages: 基础包名
            exclude_patterns: 排除模式列表
            include_patterns: 包含模式列表
            filters: 自定义过滤器列表
        """
        self.scan_packages.extend(base_packages)

        # 配置扫描器
        if exclude_patterns:
            for pattern in exclude_patterns:
                self.scanner.add_exclude_pattern(pattern)

        if include_patterns:
            for pattern in include_patterns:
                self.scanner.add_include_pattern(pattern)

        if filters:
            for filter_func in filters:
                self.scanner.add_filter(filter_func)

    def register_classes(self, *classes: Type):
        """注册指定类进行扫描"""
        self.scan_classes.extend(classes)

    def refresh(self):
        """刷新应用上下文 - 执行扫描和Bean注册"""
        # 执行包扫描
        if self.scan_packages:
            bean_definitions = self.scanner.scan_packages(*self.scan_packages)
            for definition in bean_definitions:
                self.bean_factory.register_bean_definition(definition)

        # 执行类扫描
        if self.scan_classes:
            bean_definitions = self.scanner.scan_classes(*self.scan_classes)
            for definition in bean_definitions:
                self.bean_factory.register_bean_definition(definition)

        # 预实例化非延迟的单例Bean
        self.bean_factory.pre_instantiate_singletons()

    def get_bean_by_type(self, bean_type: Type, qualifier: Optional[str] = None):
        """根据类型获取Bean实例"""
        return self.bean_factory.get_bean_by_type(bean_type, qualifier)

    def get_bean_names_for_type(self, bean_type: Type) -> List[str]:
        """根据类型获取Bean名称列表"""
        return self.bean_factory.get_bean_names_for_type(bean_type)

    def add_property_source(self, source: dict):
        """添加属性源"""
        self.value_resolver.add_properties(source)

    def load_properties_from_file(self, file_path: str):
        """从文件加载属性"""
        self.value_resolver.load_from_file(file_path)

    def register_configuration(self, config_class: Type):
        """注册配置类"""
        config_instance = self.config_binder.bind_properties(config_class)

        # 注册配置类本身为Bean
        self.register_bean(config_class)

        # 注册配置类中定义的Bean
        bean_definitions = self.config_binder.collect_bean_definitions(config_instance)
        for bean_def in bean_definitions:
            if 'method' in bean_def and bean_def['method']:
                # 创建工厂方法的Bean定义
                factory_name = f"{config_class.__name__}.{bean_def['method'].__name__}"
                definition = BeanDefinition(
                    bean_type=config_class,
                    bean_name=bean_def['name'],
                    factory_method=bean_def['method'],
                    scope=ScopeType.SINGLETON
                )
                self.bean_factory.register_bean_definition(definition)

    def get_scanner_stats(self) -> dict:
        """获取扫描统计信息"""
        return self.scanner.get_scanned_count()

    def close(self):
        """关闭应用上下文"""
        self.bean_factory.destroy_singletons()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
