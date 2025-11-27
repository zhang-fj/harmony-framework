"""
Harmony容器模块 - Bean容器相关功能
"""

# 延迟导入，避免循环导入
def __getattr__(name: str):
    """
    延迟导入容器组件，避免循环依赖

    Args:
        name: 要导入的组件名称

    Returns:
        对应的类或实例

    Raises:
        AttributeError: 当组件不存在时

    Note:
        PyCharm可能无法正确识别这些动态导入，这是正常的。
        运行时导入工作正常，IDE警告可以忽略。
    """
    if name == 'ScopeType':
        from .scope import ScopeType
        return ScopeType
    elif name == 'ScopeManager':
        from .scope import ScopeManager
        return ScopeManager
    elif name == 'enhanced_scope_registry':
        from .scope import enhanced_scope_registry
        return enhanced_scope_registry
    elif name == 'EnhancedScopeRegistry':
        from .scope import EnhancedScopeRegistry
        return EnhancedScopeRegistry
    elif name == 'ScopeMetadata':
        from .scope import ScopeMetadata
        return ScopeMetadata
    elif name == 'BeanCreator':
        from .bean_creator import BeanCreator
        return BeanCreator
    elif name == 'DependencyResolver':
        from .dependency_resolver import DependencyResolver
        return DependencyResolver
    elif name == 'InjectionProcessor':
        from .injection_processor import InjectionProcessor
        return InjectionProcessor
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'BeanCreator',
    'DependencyResolver',
    'InjectionProcessor',
    'ScopeType',
    'ScopeManager',
    'ScopeMetadata',
    'enhanced_scope_registry',
    'EnhancedScopeRegistry'
]