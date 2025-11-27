"""Harmony框架生命周期注解"""

import functools
from enum import Enum
from typing import Callable, Optional, Any


class LifecyclePhase(Enum):
    """生命周期阶段"""
    CONSTRUCTION = "construction"  # 构造阶段
    DEPENDENCY_INJECTION = "dependency_injection"  # 依赖注入阶段
    INITIALIZATION = "initialization"  # 初始化阶段
    READY = "ready"  # 就绪阶段
    DESTRUCTION = "destruction"  # 销毁阶段


class LifecycleCallback:
    """生命周期回调"""

    def __init__(self, phase: LifecyclePhase, order: int = 0):
        self.phase = phase
        self.order = order
        self.method_name: Optional[str] = None
        self.callback_func: Optional[Callable] = None

    def __call__(self, func_or_class):
        """支持装饰器语法"""
        if callable(func_or_class):
            # 方法装饰器
            func_or_class.__harmony_lifecycle__ = self
            func_or_class.__harmony_lifecycle_phase__ = self.phase
            func_or_class.__harmony_lifecycle_order__ = self.order
            return func_or_class
        else:
            # 类装饰器（预留）
            return func_or_class


def post_construct(order: int = 0):
    """PostConstruct注解 - 在依赖注入完成后调用"""
    return LifecycleCallback(LifecyclePhase.INITIALIZATION, order)


def pre_destroy(order: int = 0):
    """PreDestroy注解 - 在销毁前调用"""
    return LifecycleCallback(LifecyclePhase.DESTRUCTION, order)


class PostConstruct:
    """初始化后方法注解 - 兼容版本"""

    def __call__(self, method):
        method.__harmony_post_construct__ = True
        return method


class PreDestroy:
    """销毁前方法注解 - 兼容版本"""

    def __call__(self, method):
        method.__harmony_pre_destroy__ = True
        return method


def bean_init(order: int = 0):
    """Bean初始化注解 - 在Bean创建完成后调用"""
    return LifecycleCallback(LifecyclePhase.READY, order)


def lifecycle_hook(phase: LifecyclePhase, order: int = 0):
    """通用生命周期钩子"""
    return LifecycleCallback(phase, order)


class LifecycleManager:
    """生命周期管理器"""

    def __init__(self):
        self.callbacks: dict[str, list[LifecycleCallback]] = {}
        self.global_callbacks: dict[LifecyclePhase, list[LifecycleCallback]] = {}

    def register_callback(self, bean_name: str, callback: LifecycleCallback) -> None:
        """注册Bean级别的生命周期回调"""
        if bean_name not in self.callbacks:
            self.callbacks[bean_name] = []
        self.callbacks[bean_name].append(callback)

    def register_global_callback(self, phase: LifecyclePhase, callback: Callable, order: int = 0) -> None:
        """注册全局生命周期回调"""
        if phase not in self.global_callbacks:
            self.global_callbacks[phase] = []

        lifecycle_callback = LifecycleCallback(phase, order)
        lifecycle_callback.callback_func = callback
        self.global_callbacks[phase].append(lifecycle_callback)

    def execute_phase(self, bean_name: str, phase: LifecyclePhase, bean_instance: Any) -> None:
        """执行特定阶段的生命周期回调"""
        # 执行Bean级别的回调
        if bean_name in self.callbacks:
            bean_callbacks = self.callbacks[bean_name]
            phase_callbacks = [cb for cb in bean_callbacks if cb.phase == phase]
            phase_callbacks.sort(key=lambda x: x.order)

            for callback in phase_callbacks:
                self._execute_callback(callback, bean_instance)

        # 执行全局回调
        if phase in self.global_callbacks:
            global_callbacks = self.global_callbacks[phase]
            global_callbacks.sort(key=lambda x: x.order)

            for callback in global_callbacks:
                if callback.callback_func:
                    try:
                        callback.callback_func(bean_name, bean_instance)
                    except Exception:
                        # 全局回调异常不应该影响Bean创建
                        pass

    def _execute_callback(self, callback: LifecycleCallback, bean_instance: Any) -> None:
        """执行回调"""
        try:
            if callback.method_name:
                # 通过方法名调用
                if hasattr(bean_instance, callback.method_name):
                    method = getattr(bean_instance, callback.method_name)
                    method()
            else:
                # 通过函数调用
                if callback.callback_func:
                    callback.callback_func(bean_instance)
        except Exception:
            # 生命周期回调异常不应该影响Bean创建
            pass

    def scan_class_callbacks(self, bean_class: type, bean_name: str) -> None:
        """扫描类中的生命周期回调注解"""
        for attr_name in dir(bean_class):
            if attr_name.startswith('__'):
                continue

            attr = getattr(bean_class, attr_name)
            if hasattr(attr, '__harmony_lifecycle__'):
                lifecycle_callback = getattr(attr, '__harmony_lifecycle__')
                lifecycle_callback.method_name = attr_name
                self.register_callback(bean_name, lifecycle_callback)

            # 兼容旧版本注解
            elif hasattr(attr, '__harmony_post_construct__'):
                callback = LifecycleCallback(LifecyclePhase.INITIALIZATION)
                callback.method_name = attr_name
                self.register_callback(bean_name, callback)

            elif hasattr(attr, '__harmony_pre_destroy__'):
                callback = LifecycleCallback(LifecyclePhase.DESTRUCTION)
                callback.method_name = attr_name
                self.register_callback(bean_name, callback)

    def destroy_bean(self, bean_name: str, bean_instance: Any) -> None:
        """销毁Bean"""
        self.execute_phase(bean_name, LifecyclePhase.DESTRUCTION, bean_instance)


def bean_aware(cls):
    """标记Bean需要感知生命周期"""

    def __init__(original_init):
        @functools.wraps(original_init)
        def wrapper(self, *args, **kwargs):
            self.__harmony_bean_name__ = None
            self.__harmony_lifecycle_manager__ = None
            return original_init(self, *args, **kwargs)

        return wrapper

    if hasattr(cls, '__init__'):
        cls.__init__ = __init__(cls.__init__)

    # 添加生命周期方法
    def set_bean_name(self, bean_name: str):
        self.__harmony_bean_name__ = bean_name

    def set_lifecycle_manager(self, manager: LifecycleManager):
        self.__harmony_lifecycle_manager__ = manager

    def get_bean_name(self) -> str:
        return getattr(self, '__harmony_bean_name__', None)

    def get_lifecycle_manager(self) -> LifecycleManager | None:
        return getattr(self, '__harmony_lifecycle_manager__', None)

    cls.set_bean_name = set_bean_name
    cls.set_lifecycle_manager = set_lifecycle_manager
    cls.get_bean_name = get_bean_name
    cls.get_lifecycle_manager = get_lifecycle_manager

    return cls


class SmartInitializingSingleton:
    """智能初始化单例接口"""

    def after_properties_set(self) -> None:
        """在属性设置后调用"""
        pass

    def destroy(self) -> None:
        """销毁时调用"""
        pass


class DisposableBean:
    """可销毁Bean接口"""

    def destroy(self) -> None:
        """销毁方法"""
        pass


class ApplicationContextAware:
    """应用上下文感知接口"""

    def __init__(self):
        self.context = None

    def set_application_context(self, context) -> None:
        """设置应用上下文"""
        self.context = context
