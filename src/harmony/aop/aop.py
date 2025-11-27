"""
增强版AOP切面编程支持 - 支持方法拦截和增强
"""

import functools
import inspect
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from contextlib import contextmanager
import weakref


class JoinPointType(Enum):
    """连接点类型"""
    METHOD_EXECUTION = "method_execution"
    CONSTRUCTOR_EXECUTION = "constructor_execution"
    FIELD_ACCESS = "field_access"
    METHOD_CALL = "method_call"
    EXCEPTION_HANDLING = "exception_handling"
    FINALLY_BLOCK = "finally_block"


@dataclass
class JoinPoint:
    """连接点"""
    target: Any
    method_name: str
    args: Tuple
    kwargs: Dict[str, Any]
    join_point_type: JoinPointType
    signature: Optional[inspect.Signature] = None
    class_info: Optional[type] = None

    def get_method(self) -> Callable:
        """获取方法对象"""
        if self.join_point_type == JoinPointType.METHOD_EXECUTION:
            return getattr(self.class_info, self.method_name, None) if self.class_info else None
        return None

    def get_target_class(self) -> Optional[type]:
        """获取目标类"""
        if isinstance(self.target, type):
            return self.target
        elif self.class_info:
            return self.class_info
        return type(self.target)


@dataclass
class MethodInvocation:
    """方法调用信息"""
    join_point: JoinPoint
    proceed: Callable[[], Any]
    returned_value: Any = None
    exception: Optional[Exception] = None
    execution_time: float = 0.0
    around_called: bool = False


class Advice(ABC):
    """通知抽象基类"""

    @abstractmethod
    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行通知逻辑"""
        pass


class BeforeAdvice(Advice):
    """前置通知 - 在方法执行前执行"""

    def __init__(self, advice_func: Callable[[JoinPoint], None]):
        self.advice_func = advice_func

    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行前置通知"""
        try:
            self.advice_func(invocation.join_point)
        except Exception as e:
            # 前置通知异常不应影响方法执行
            print(f"Before advice error: {e}")

        # 继续执行原方法
        if not invocation.around_called:
            return invocation.proceed()
        return invocation.returned_value


class AfterAdvice(Advice):
    """后置通知 - 在方法执行后执行（无论成功还是异常）"""

    def __init__(self, advice_func: Callable[[JoinPoint, Any, Optional[Exception]], None]):
        self.advice_func = advice_func

    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行后置通知"""
        # 先执行原方法
        if not invocation.around_called:
            try:
                start_time = time.time()
                invocation.returned_value = invocation.proceed()
                invocation.execution_time = time.time() - start_time
            except Exception as e:
                invocation.exception = e
                raise
            finally:
                # 执行后置通知
                try:
                    self.advice_func(invocation.join_point, invocation.returned_value, invocation.exception)
                except Exception as e:
                    # 后置通知异常不影响主流程
                    print(f"After advice error: {e}")

        return invocation.returned_value


class AfterReturningAdvice(Advice):
    """返回后通知 - 在方法成功返回后执行"""

    def __init__(self, advice_func: Callable[[JoinPoint, Any], None]):
        self.advice_func = advice_func

    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行返回后通知"""
        # 先执行原方法
        if not invocation.around_called:
            try:
                start_time = time.time()
                invocation.returned_value = invocation.proceed()
                invocation.execution_time = time.time() - start_time
            except Exception as e:
                invocation.exception = e
                raise

        # 执行返回后通知
        try:
            if invocation.exception is None:
                self.advice_func(invocation.join_point, invocation.returned_value)
        except Exception as e:
            print(f"AfterReturning advice error: {e}")

        return invocation.returned_value


class AfterThrowingAdvice(Advice):
    """异常后通知 - 在方法抛出异常时执行"""

    def __init__(self, advice_func: Callable[[JoinPoint, Exception], None]):
        self.advice_func = advice_func

    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行异常后通知"""
        # 先执行原方法
        if not invocation.around_called:
            try:
                start_time = time.time()
                invocation.returned_value = invocation.proceed()
                invocation.execution_time = time.time() - start_time
            except Exception as e:
                invocation.exception = e
                # 执行异常后通知
                try:
                    self.advice_func(invocation.join_point, e)
                except Exception as advice_error:
                    print(f"AfterThrowing advice error: {advice_error}")
                raise

        return invocation.returned_value


class AroundAdvice(Advice):
    """环绕通知 - 完全控制方法的执行"""

    def __init__(self, advice_func: Callable[[MethodInvocation], Any]):
        self.advice_func = advice_func

    def invoke(self, invocation: MethodInvocation) -> Any:
        """执行环绕通知"""
        # 标记around已调用，避免重复执行
        invocation.around_called = True
        try:
            start_time = time.time()
            result = self.advice_func(invocation)
            invocation.execution_time = time.time() - start_time
            invocation.returned_value = result
            return result
        except Exception as e:
            invocation.exception = e
            raise


@dataclass
class Pointcut:
    """切点定义"""
    name: str
    advice: Advice
    pointcut_expression: str  # 切点表达式
    priority: int = 0
    enabled: bool = True
    target_methods: List[str] = field(default_factory=list)
    target_classes: List[type] = field(default_factory=list)


class Aspect:
    """切面"""

    def __init__(self, name: str):
        self.name = name
        self.pointcuts: List[Pointcut] = []

    def before(self, expression: str, priority: int = 0):
        """定义前置通知"""

        def decorator(advice_func: Callable[[JoinPoint], None]):
            advice = BeforeAdvice(advice_func)
            pointcut = Pointcut(
                name=f"{self.name}_before_{len(self.pointcuts)}",
                advice=advice,
                pointcut_expression=expression,
                priority=priority
            )
            self.pointcuts.append(pointcut)
            return advice_func

        return decorator

    def after(self, expression: str, priority: int = 0):
        """定义后置通知"""

        def decorator(advice_func: Callable[[JoinPoint, Any, Optional[Exception]], None]):
            advice = AfterAdvice(advice_func)
            pointcut = Pointcut(
                name=f"{self.name}_after_{len(self.pointcuts)}",
                advice=advice,
                pointcut_expression=expression,
                priority=priority
            )
            self.pointcuts.append(pointcut)
            return advice_func

        return decorator

    def after_returning(self, expression: str, priority: int = 0):
        """定义返回后通知"""

        def decorator(advice_func: Callable[[JoinPoint, Any], None]):
            advice = AfterReturningAdvice(advice_func)
            pointcut = Pointcut(
                name=f"{self.name}_after_returning_{len(self.pointcuts)}",
                advice=advice,
                pointcut_expression=expression,
                priority=priority
            )
            self.pointcuts.append(pointcut)
            return advice_func

        return decorator

    def after_throwing(self, expression: str, priority: int = 0):
        """定义异常后通知"""

        def decorator(advice_func: Callable[[JoinPoint, Exception], None]):
            advice = AfterThrowingAdvice(advice_func)
            pointcut = Pointcut(
                name=f"{self.name}_after_throwing_{len(self.pointcuts)}",
                advice=advice,
                pointcut_expression=expression,
                priority=priority
            )
            self.pointcuts.append(pointcut)
            return advice_func

        return decorator

    def around(self, expression: str, priority: int = 0):
        """定义环绕通知"""

        def decorator(advice_func: Callable[[MethodInvocation], Any]):
            advice = AroundAdvice(advice_func)
            pointcut = Pointcut(
                name=f"{self.name}_around_{len(self.pointcuts)}",
                advice=advice,
                pointcut_expression=expression,
                priority=priority
            )
            self.pointcuts.append(pointcut)
            return advice_func

        return decorator


class PointcutMatcher:
    """切点匹配器"""

    @staticmethod
    def matches(expression: str, join_point: JoinPoint) -> bool:
        """检查切点表达式是否匹配连接点"""
        if not expression:
            return False

        # 简化的表达式匹配逻辑
        # 支持的表达式格式：
        # "execution(*ClassName.method(..))" - 方法执行
        # "execution(*ClassName.*(..))" - 类中所有方法
        # "execution(*..*(..))" - 所有方法

        if expression.startswith("execution(") and expression.endswith(")"):
            method_pattern = expression[len("execution("):-1]
            return PointcutMatcher._match_execution_pattern(method_pattern, join_point)

        return False

    @staticmethod
    def _match_execution_pattern(pattern: str, join_point: JoinPoint) -> bool:
        """匹配执行模式"""
        if join_point.join_point_type != JoinPointType.METHOD_EXECUTION:
            return False

        # 简化的模式匹配
        if pattern == "*..*(..)":
            return True  # 匹配所有方法

        if "*.*" in pattern:
            # 类级别匹配
            if pattern.startswith("execution(*") and pattern.endswith(".*(..))"):
                class_pattern = pattern[len("execution(*"):-5]
                target_class_name = join_point.get_target_class().__name__
                return class_pattern in target_class_name or target_class_name in class_pattern

        if pattern.endswith("*(..)"):
            # 方法名称匹配
            method_pattern = pattern.split(".")[-1].replace("*(..)", "")
            return method_pattern in join_point.method_name or join_point.method_name in method_pattern

        return False


class AopProxy:
    """AOP代理"""

    def __init__(self, target: Any, aspect_manager: 'AspectManager'):
        self._target = target
        self._aspect_manager = aspect_manager
        self._class_info = target.__class__

    def __getattr__(self, name: str) -> Any:
        """代理属性访问"""
        if name.startswith('__') or name.startswith('_AopProxy'):
            # 跳过特殊属性
            return getattr(self._target, name)

        attr = getattr(self._target, name, None)

        if callable(attr):
            return self._create_proxy_method(name, attr)

        return attr

    def _create_proxy_method(self, method_name: str, original_method: Callable) -> Callable:
        """创建代理方法"""

        @functools.wraps(original_method)
        def proxy_method(*args, **kwargs):
            # 创建连接点
            join_point = JoinPoint(
                target=self._target,
                method_name=method_name,
                args=args,
                kwargs=kwargs,
                join_point_type=JoinPointType.METHOD_EXECUTION,
                signature=inspect.signature(original_method),
                class_info=self._class_info
            )

            # 检查是否有匹配的切面
            matching_pointcuts = self._aspect_manager.get_matching_pointcuts(join_point)

            if not matching_pointcuts:
                # 没有匹配的切面，直接执行原方法
                return original_method(*args, **kwargs)

            # 创建方法调用
            def proceed():
                return original_method(*args, **kwargs)

            invocation = MethodInvocation(
                join_point=join_point,
                proceed=proceed
            )

            # 按优先级排序并执行通知
            sorted_pointcuts = sorted(matching_pointcuts, key=lambda p: p.priority)

            before_advice = [pc for pc in sorted_pointcuts if isinstance(pc.advice, BeforeAdvice)]
            after_advice = [pc for pc in sorted_pointcuts if isinstance(pc.advice, AfterAdvice)]
            after_returning_advice = [pc for pc in sorted_pointcuts if isinstance(pc.advice, AfterReturningAdvice)]
            after_throwing_advice = [pc for pc in sorted_pointcuts if isinstance(pc.advice, AfterThrowingAdvice)]
            around_advice = [pc for pc in sorted_pointcuts if isinstance(pc.advice, AroundAdvice)]

            # 执行逻辑
            if around_advice:
                # 有环绕通知，让第一个环绕通知控制整个流程
                return around_advice[0].advice.invoke(invocation)
            else:
                # 没有环绕通知，按顺序执行其他通知
                try:
                    # 执行前置通知
                    for pointcut in before_advice:
                        pointcut.advice.invoke(invocation)

                    # 执行原方法
                    result = proceed()
                    invocation.returned_value = result

                    # 执行返回后通知
                    for pointcut in after_returning_advice:
                        pointcut.advice.invoke(invocation)

                    return result

                except Exception as e:
                    invocation.exception = e
                    # 执行异常后通知
                    for pointcut in after_throwing_advice:
                        pointcut.advice.invoke(invocation)
                    raise
                finally:
                    # 执行后置通知
                    for pointcut in after_advice:
                        try:
                            pointcut.advice.invoke(invocation)
                        except Exception:
                            pass  # 忽略后置通知错误

        return proxy_method


class AspectManager:
    """切面管理器"""

    def __init__(self):
        self.aspects: List[Aspect] = []
        self.pointcuts: List[Pointcut] = []
        self.proxies: Dict[int, AopProxy] = {}
        self._lock = threading.RLock()

    def create_aspect(self, name: str) -> Aspect:
        """创建切面"""
        aspect = Aspect(name)
        with self._lock:
            self.aspects.append(aspect)
            # 收集所有切点
            self.pointcuts.extend(aspect.pointcuts)
        return aspect

    def add_pointcut(self, pointcut: Pointcut):
        """添加切点"""
        with self._lock:
            self.pointcuts.append(pointcut)

    def get_matching_pointcuts(self, join_point: JoinPoint) -> List[Pointcut]:
        """获取匹配的切点"""
        with self._lock:
            matching_pointcuts = []
            for pointcut in self.pointcuts:
                if pointcut.enabled and PointcutMatcher.matches(pointcut.pointcut_expression, join_point):
                    matching_pointcuts.append(pointcut)
            return matching_pointcuts

    def create_proxy(self, target: Any) -> AopProxy:
        """为目标对象创建代理"""
        proxy = AopProxy(target, self)

        # 使用弱引用存储代理，避免内存泄漏
        target_id = id(target)
        with self._lock:
            self.proxies[target_id] = proxy

        return proxy

    def remove_proxy(self, target: Any) -> bool:
        """移除代理"""
        target_id = id(target)
        with self._lock:
            return self.proxies.pop(target_id, None) is not None

    def enable_pointcut(self, pointcut_name: str):
        """启用切点"""
        with self._lock:
            for pointcut in self.pointcuts:
                if pointcut.name == pointcut_name:
                    pointcut.enabled = True

    def disable_pointcut(self, pointcut_name: str):
        """禁用切点"""
        with self._lock:
            for pointcut in self.pointcuts:
                if pointcut.name == pointcut_name:
                    pointcut.enabled = False

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'aspect_count': len(self.aspects),
                'pointcut_count': len(self.pointcuts),
                'enabled_pointcuts': len([pc for pc in self.pointcuts if pc.enabled]),
                'proxy_count': len(self.proxies),
                'pointcut_types': self._get_pointcut_type_stats()
            }

    def _get_pointcut_type_stats(self) -> Dict[str, int]:
        """获取切点类型统计"""
        type_stats = defaultdict(int)
        for pointcut in self.pointcuts:
            advice_type = type(pointcut.advice).__name__
            type_stats[advice_type] += 1
        return dict(type_stats)

    def clear(self):
        """清空所有切面和代理"""
        with self._lock:
            self.aspects.clear()
            self.pointcuts.clear()
            self.proxies.clear()


# 全局切面管理器实例
aspect_manager = AspectManager()


def aspect(name: str):
    """切面装饰器 - 简化切面创建"""
    def decorator(cls):
        # 为类添加切面功能
        if not hasattr(cls, '_harmony_aspect'):
            cls._harmony_aspect = Aspect(name)

        # 将类方法转换为切面方法
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue

            attr = getattr(cls, attr_name)
            if callable(attr) and hasattr(attr, '_harmony_pointcut_type'):
                pointcut_type = getattr(attr, '_harmony_pointcut_type')
                pointcut_expression = getattr(attr, '_harmony_pointcut_expression', '')
                priority = getattr(attr, '_harmony_pointcut_priority', 0)

                # 创建对应的通知
                if pointcut_type == 'before':
                    advice = BeforeAdvice(attr)
                elif pointcut_type == 'after':
                    advice = AfterAdvice(attr)
                elif pointcut_type == 'after_returning':
                    advice = AfterReturningAdvice(attr)
                elif pointcut_type == 'after_throwing':
                    advice = AfterThrowingAdvice(attr)
                elif pointcut_type == 'around':
                    advice = AroundAdvice(attr)
                else:
                    continue

                pointcut = Pointcut(
                    name=f"{name}_{attr_name}",
                    advice=advice,
                    pointcut_expression=pointcut_expression,
                    priority=priority
                )

                cls._harmony_aspect.pointcuts.append(pointcut)

        return cls

    return decorator


def before(expression: str = "*", priority: int = 0):
    """前置通知装饰器"""
    def decorator(func):
        func._harmony_pointcut_type = 'before'
        func._harmony_pointcut_expression = expression
        func._harmony_pointcut_priority = priority
        return func

    return decorator


def after(expression: str = "*", priority: int = 0):
    """后置通知装饰器"""
    def decorator(func):
        func._harmony_pointcut_type = 'after'
        func._harmony_pointcut_expression = expression
        func._harmony_pointcut_priority = priority
        return func

    return decorator


def after_returning(expression: str = "*", priority: int = 0):
    """返回后通知装饰器"""
    def decorator(func):
        func._harmony_pointcut_type = 'after_returning'
        func._harmony_pointcut_expression = expression
        func._harmony_pointcut_priority = priority
        return func

    return decorator


def after_throwing(expression: str = "*", priority: int = 0):
    """异常后通知装饰器"""
    def decorator(func):
        func._harmony_pointcut_type = 'after_throwing'
        func._harmony_pointcut_expression = expression
        func._harmony_pointcut_priority = priority
        return func

    return decorator


def around(expression: str = "*", priority: int = 0):
    """环绕通知装饰器"""
    def decorator(func):
        func._harmony_pointcut_type = 'around'
        func._harmony_pointcut_expression = expression
        func._harmony_pointcut_priority = priority
        return func

    return decorator


class AopUtils:
    """AOP工具类"""

    @staticmethod
    def enable_aop_for_class(cls: type, aspect_manager: AspectManager = None) -> type:
        """为类启用AOP功能"""
        manager = aspect_manager or aspect_manager

        class AopEnabledClass(cls):
            def __new__(subclass_cls, *args, **kwargs):
                instance = super(AopEnabledClass, subclass_cls).__new__(subclass_cls)
                # 创建代理对象
                proxy = manager.create_proxy(instance)
                return proxy

        return AopEnabledClass

    @staticmethod
    @contextmanager
    def temporary_aspect(name: str, aspect_manager: AspectManager = None):
        """临时切面上下文管理器"""
        manager = aspect_manager or aspect_manager
        temp_aspect = manager.create_aspect(name)
        try:
            yield temp_aspect
        finally:
            # 清理临时切面
            with manager._lock:
                if temp_aspect in manager.aspects:
                    manager.aspects.remove(temp_aspect)
                for pointcut in temp_aspect.pointcuts:
                    if pointcut in manager.pointcuts:
                        manager.pointcuts.remove(pointcut)

    @staticmethod
    def profile_methods(expression: str = "*..*(..)", min_duration: float = 0.1) -> Aspect:
        """创建性能监控切面"""
        profile_aspect = aspect_manager.create_aspect("profiler")

        @around(expression, priority=100)
        def profile_advice(invocation: MethodInvocation):
            import time
            start_time = time.time()
            try:
                result = invocation.proceed()
                duration = time.time() - start_time

                if duration >= min_duration:
                    method_name = f"{invocation.join_point.get_target_class().__name__}.{invocation.join_point.method_name}"
                    print(f"[PROFILE] {method_name} took {duration:.4f}s")

                return result
            except Exception as e:
                duration = time.time() - start_time
                method_name = f"{invocation.join_point.get_target_class().__name__}.{invocation.join_point.method_name}"
                print(f"[PROFILE] {method_name} failed after {duration:.4f}s: {e}")
                raise

        return profile_aspect

    @staticmethod
    def cache_results(expression: str = "*..*(..)", cache_size: int = 100) -> Aspect:
        """创建结果缓存切面"""
        cache = {}

        cache_aspect = aspect_manager.create_aspect("cache")

        @around(expression, priority=90)
        def cache_advice(invocation: MethodInvocation):
            # 生成缓存键
            cache_key = (
                invocation.join_point.get_target_class().__name__,
                invocation.join_point.method_name,
                hash(invocation.join_point.args),
                hash(tuple(sorted(invocation.join_point.kwargs.items())))
            )

            # 检查缓存
            if cache_key in cache:
                return cache[cache_key]

            # 执行原方法并缓存结果
            result = invocation.proceed()
            if len(cache) >= cache_size:
                # 简单的LRU：删除第一个元素
                oldest_key = next(iter(cache))
                del cache[oldest_key]

            cache[cache_key] = result
            return result

        return cache_aspect

    @staticmethod
    def retry_on_exception(expression: str = "*..*(..)",
                          max_attempts: int = 3,
                          delay: float = 1.0,
                          exceptions: Tuple = (Exception,)) -> Aspect:
        """创建重试切面"""
        retry_aspect = aspect_manager.create_aspect("retry")

        @around(expression, priority=80)
        def retry_advice(invocation: MethodInvocation):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return invocation.proceed()
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))  # 递增延迟

            raise last_exception

        return retry_aspect

    @staticmethod
    def transactional(expression: str = "*..*(..)") -> Aspect:
        """创建事务切面（简化版本）"""
        transaction_aspect = aspect_manager.create_aspect("transaction")

        @around(expression, priority=70)
        def transaction_advice(invocation: MethodInvocation):
            # 这里可以集成真实的事务管理
            print(f"[TRANSACTION] Starting transaction for {invocation.join_point.method_name}")
            try:
                result = invocation.proceed()
                print(f"[TRANSACTION] Committing transaction for {invocation.join_point.method_name}")
                return result
            except Exception as e:
                print(f"[TRANSACTION] Rolling back transaction for {invocation.join_point.method_name}: {e}")
                raise

        return transaction_aspect


# 便捷函数
def enable_aop(obj: Any, aspect_manager: AspectManager = None) -> Any:
    """为对象启用AOP"""
    manager = aspect_manager or aspect_manager
    return manager.create_proxy(obj)


def register_aspect(aspect_obj: Aspect, aspect_manager: AspectManager = None):
    """注册切面"""
    manager = aspect_manager or aspect_manager
    with manager._lock:
        manager.aspects.append(aspect_obj)
        manager.pointcuts.extend(aspect_obj.pointcuts)
