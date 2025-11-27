import inspect
from typing import Optional, Type

from ..container.scope import ScopeType
from ..core.bean_definition import BeanDefinition


def component(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON,
              primary: bool = False, lazy: bool = False):
    """组件注解 - 增强版本"""

    def decorator(cls):
        # 记录组件元数据
        cls.__harmony_component_metadata__ = {
            'bean_name': bean_name,
            'scope': scope,
            'primary': primary,
            'lazy': lazy
        }
        # 设置简单的标记
        cls.__harmony_component__ = True
        return cls

    return decorator


def service(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """服务层注解"""

    def decorator(cls):
        # 记录服务元数据
        cls.__harmony_service_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_service__ = True
        return cls

    return decorator


def repository(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """数据访问层注解"""

    def decorator(cls):
        # 记录仓库元数据
        cls.__harmony_repository_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_repository__ = True
        return cls

    return decorator


def controller(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """控制层注解"""

    def decorator(cls):
        # 记录控制器元数据
        cls.__harmony_controller_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_controller__ = True
        return cls

    return decorator


def constructor_autowired(cls):
    """构造器自动注入注解"""
    # 标记需要构造器注入
    cls.__harmony_constructor_autowired__ = True
    return cls


def bean(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON,
         primary: bool = False, lazy: bool = False,
         init_method: Optional[str] = None, destroy_method: Optional[str] = None):
    """通用Bean注解"""

    def decorator(cls):
        cls.__harmony_bean__ = {
            'bean_name': bean_name,
            'scope': scope,
            'primary': primary,
            'lazy': lazy,
            'init_method': init_method,
            'destroy_method': destroy_method
        }
        return cls

    return decorator


def create_bean_definition(bean_class: Type) -> BeanDefinition:
    """从类创建Bean定义"""
    # 检查Bean注解
    bean_metadata = getattr(bean_class, '__harmony_bean__', {})
    component_metadata = getattr(bean_class, '__harmony_component_metadata__', {})
    bean_name = bean_metadata.get('bean_name') or component_metadata.get('bean_name')

    # 合并元数据
    scope = bean_metadata.get('scope') or component_metadata.get('scope', ScopeType.SINGLETON)
    primary = bean_metadata.get('primary') or component_metadata.get('primary', False)
    lazy = bean_metadata.get('lazy') or component_metadata.get('lazy', False)

    definition = BeanDefinition(
        bean_type=bean_class,
        bean_name=bean_name,
        scope=scope,
        primary=primary,
        lazy=lazy,
        init_method=bean_metadata.get('init_method'),
        destroy_method=bean_metadata.get('destroy_method')
    )

    # 解析构造器参数
    if hasattr(bean_class, '__harmony_constructor_autowired__'):
        _parse_constructor_autowired(bean_class, definition)

    return definition


def _parse_constructor_autowired(bean_class: Type, definition: BeanDefinition):
    """解析构造器自动注入"""
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
        # 解析失败时忽略
        pass
