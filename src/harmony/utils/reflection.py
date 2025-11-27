import inspect
from typing import Type, List, Callable


def get_class_methods(cls: Type) -> List[Callable]:
    """获取类的所有方法"""
    return [method for method in cls.__dict__.values()
            if inspect.isfunction(method) or inspect.ismethod(method)]


def has_decorator(method: Callable, decorator_name: str) -> bool:
    """检查方法是否有指定装饰器"""
    return hasattr(method, decorator_name)
