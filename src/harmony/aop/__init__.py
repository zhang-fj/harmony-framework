"""
Harmony AOP模块 - 面向切面编程
"""

# 直接导入核心的、常用的组件
from .aop import JoinPoint, JoinPointType, MethodInvocation

# 延迟导入复杂的组件，避免循环依赖
def __getattr__(name: str):
    """
    延迟导入AOP组件，避免循环依赖

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
    if name == 'Aspect':
        from .aop import Aspect
        return Aspect
    elif name == 'BeforeAdvice':
        from .aop import BeforeAdvice
        return BeforeAdvice
    elif name == 'AfterAdvice':
        from .aop import AfterAdvice
        return AfterAdvice
    elif name == 'AfterReturningAdvice':
        from .aop import AfterReturningAdvice
        return AfterReturningAdvice
    elif name == 'AfterThrowingAdvice':
        from .aop import AfterThrowingAdvice
        return AfterThrowingAdvice
    elif name == 'AroundAdvice':
        from .aop import AroundAdvice
        return AroundAdvice
    elif name == 'AspectManager':
        from .aop import AspectManager
        return AspectManager
    elif name == 'aspect_manager':
        from .aop import aspect_manager
        return aspect_manager
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # 直接导入的核心组件
    'JoinPoint',
    'JoinPointType',
    'MethodInvocation',

    # 延迟导入的组件
    'Aspect',
    'BeforeAdvice',
    'AfterAdvice',
    'AfterReturningAdvice',
    'AfterThrowingAdvice',
    'AroundAdvice',
    'AspectManager',
    'aspect_manager'
]
