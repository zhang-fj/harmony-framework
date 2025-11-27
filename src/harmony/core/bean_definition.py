from dataclasses import dataclass, field
from typing import Type, Any, List, Dict, Optional, Callable, Set

from ..container.scope import ScopeType


@dataclass
class ConstructorArgument:
    """构造器参数定义"""
    name: str
    param_type: Type
    required: bool = True
    default_value: Any = None
    qualifier: Optional[str] = None


@dataclass
class DependencyDefinition:
    """依赖定义"""
    name: str
    dependency_type: Type
    required: bool = True
    qualifier: Optional[str] = None


@dataclass
class BeanDefinition:
    """Bean定义类 - 增强版"""

    bean_type: Type
    bean_name: Optional[str] = None
    scope: ScopeType = ScopeType.SINGLETON
    primary: bool = False
    lazy: bool = False
    dependencies: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    init_method: Optional[str] = None
    destroy_method: Optional[str] = None
    factory_method: Optional[Callable] = None
    factory_bean: Optional[str] = None

    # 新增字段
    constructor_args: List[ConstructorArgument] = field(default_factory=list)
    field_dependencies: List[DependencyDefinition] = field(default_factory=list)
    setter_dependencies: List[DependencyDefinition] = field(default_factory=list)
    interfaces: Set[Type] = field(default_factory=set)
    parent_class: Optional[Type] = None

    def __post_init__(self):
        """初始化后处理"""
        if not self.bean_name:
            # 使用类名首字母小写作为默认bean名称
            if hasattr(self.bean_type, '__name__'):
                self.bean_name = self.bean_type.__name__[0].lower() + self.bean_type.__name__[1:]
            else:
                # 对于内置类型，直接使用类型名
                type_name = str(self.bean_type)
                self.bean_name = type_name[0].lower() + type_name[1:] if type_name else "unnamed"

        # 自动获取接口信息 - 只对自定义类生效
        if hasattr(self.bean_type, '__interfaces__'):
            self.interfaces = set(self.bean_type.__interfaces__)
        elif hasattr(self.bean_type, '__bases__') and self.bean_type.__bases__:
            # 对于有基类的类型，获取其实现的接口
            self.interfaces = set()
            for base in self.bean_type.__bases__:
                if hasattr(base, '__interfaces__'):
                    self.interfaces.update(base.__interfaces__)
        else:
            self.interfaces = set()

        # 获取父类 - 只对自定义类生效
        if hasattr(self.bean_type, '__bases__') and self.bean_type.__bases__:
            self.parent_class = self.bean_type.__bases__[0]
        else:
            self.parent_class = None

    def add_dependency(self, dependency_name: str) -> 'BeanDefinition':
        """添加依赖 - 支持链式调用"""
        if dependency_name not in self.dependencies:
            self.dependencies.append(dependency_name)
        return self

    def add_constructor_arg(self, name: str, param_type: Type, required: bool = True,
                            default_value: Any = None, qualifier: Optional[str] = None) -> 'BeanDefinition':
        """添加构造器参数"""
        arg = ConstructorArgument(name, param_type, required, default_value, qualifier)
        self.constructor_args.append(arg)
        return self

    def add_field_dependency(self, name: str, dependency_type: Type,
                             required: bool = True, qualifier: Optional[str] = None) -> 'BeanDefinition':
        """添加字段依赖"""
        dep = DependencyDefinition(name, dependency_type, required, qualifier)
        self.field_dependencies.append(dep)
        return self

    def set_property(self, name: str, value: Any) -> 'BeanDefinition':
        """设置属性 - 支持链式调用"""
        self.properties[name] = value
        return self

    def is_singleton(self) -> bool:
        """判断是否为单例"""
        return self.scope == ScopeType.SINGLETON

    def is_prototype(self) -> bool:
        """判断是否为原型"""
        return self.scope == ScopeType.PROTOTYPE

    def get_all_dependencies(self) -> List[str]:
        """获取所有依赖名称"""
        return list(set(self.dependencies + [dep.name for dep in self.field_dependencies]))

    def __hash__(self) -> int:
        """实现hash方法，使BeanDefinition可以作为字典键"""
        return hash((self.bean_type, self.bean_name, self.scope))

    def __eq__(self, other) -> bool:
        """实现equals方法"""
        if not isinstance(other, BeanDefinition):
            return False
        return (self.bean_type == other.bean_type and
                self.bean_name == other.bean_name and
                self.scope == other.scope)

    def __str__(self) -> str:
        type_name = getattr(self.bean_type, '__name__', str(self.bean_type))
        return f"BeanDefinition(name={self.bean_name}, type={type_name}, scope={self.scope.value})"
