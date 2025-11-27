"""
生命周期事件系统 - 支持事件驱动的Bean生命周期管理
"""

import threading
import time
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Type


class EventType(Enum):
    """事件类型"""
    BEAN_CREATED = "bean_created"
    BEAN_DESTROYED = "bean_destroyed"
    BEAN_INITIALIZED = "bean_initialized"
    BEAN_CONFIGURED = "bean_configured"
    SCOPE_CHANGED = "scope_changed"
    CONTAINER_STARTED = "container_started"
    CONTAINER_STOPPED = "container_stopped"
    CONTAINER_REFRESHED = "container_refreshed"
    CUSTOM = "custom"


@dataclass
class LifecycleEvent:
    """生命周期事件"""
    event_type: EventType
    source: Any
    bean_name: Optional[str] = None
    bean_type: Optional[Type] = None
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Exception] = None


@dataclass
class EventSubscription:
    """事件订阅"""
    event_type: EventType
    listener: Callable[[LifecycleEvent], None]
    priority: int = 0
    filter_func: Optional[Callable[[LifecycleEvent], bool]] = None
    weak_ref: bool = False
    subscription_id: str = ""


class EventListener(ABC):
    """事件监听器抽象基类"""

    @abstractmethod
    def handle_event(self, event: LifecycleEvent) -> None:
        """处理事件"""
        pass

    def get_supported_event_types(self) -> List[EventType]:
        """获取支持的事件类型"""
        return []

    def get_priority(self) -> int:
        """获取优先级，数值越小优先级越高"""
        return 0


class AsyncEventListener(EventListener):
    """异步事件监听器"""

    def __init__(self, listener: Callable[[LifecycleEvent], None],
                 supported_types: List[EventType] = None, priority: int = 0):
        self.listener = listener
        self.supported_types = supported_types or []
        self.priority = priority

    def handle_event(self, event: LifecycleEvent) -> None:
        """异步处理事件"""
        try:
            if not self.supported_types or event.event_type in self.supported_types:
                self.listener(event)
        except Exception as e:
            # 记录错误但不中断其他监听器
            print(f"Async event listener error: {e}")

    def get_supported_event_types(self) -> List[EventType]:
        return self.supported_types

    def get_priority(self) -> int:
        return self.priority


class EventMetrics:
    """事件系统指标"""

    def __init__(self):
        self._lock = threading.Lock()
        self._events_published: Dict[EventType, int] = defaultdict(int)
        self._events_processed: Dict[EventType, int] = defaultdict(int)
        self._event_errors: Dict[EventType, int] = defaultdict(int)
        self._processing_times: Dict[EventType, List[float]] = defaultdict(list)
        self._subscription_count = 0
        self._listener_count = 0

    def record_event_published(self, event_type: EventType):
        """记录事件发布"""
        with self._lock:
            self._events_published[event_type] += 1

    def record_event_processed(self, event_type: EventType, processing_time: float):
        """记录事件处理"""
        with self._lock:
            self._events_processed[event_type] += 1
            self._processing_times[event_type].append(processing_time)

    def record_event_error(self, event_type: EventType):
        """记录事件处理错误"""
        with self._lock:
            self._event_errors[event_type] += 1

    def increment_subscription(self):
        """增加订阅数"""
        with self._lock:
            self._subscription_count += 1

    def decrement_subscription(self):
        """减少订阅数"""
        with self._lock:
            self._subscription_count = max(0, self._subscription_count - 1)

    def increment_listener(self):
        """增加监听器数"""
        with self._lock:
            self._listener_count += 1

    def decrement_listener(self):
        """减少监听器数"""
        with self._lock:
            self._listener_count = max(0, self._listener_count - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标统计"""
        with self._lock:
            avg_times = {}
            for event_type, times in self._processing_times.items():
                if times:
                    avg_times[event_type.value] = sum(times) / len(times)

            return {
                'events_published': {et.value: count for et, count in self._events_published.items()},
                'events_processed': {et.value: count for et, count in self._events_processed.items()},
                'event_errors': {et.value: count for et, count in self._event_errors.items()},
                'average_processing_times': avg_times,
                'subscription_count': self._subscription_count,
                'listener_count': self._listener_count,
                'total_events': sum(self._events_published.values())
            }

    def reset_metrics(self):
        """重置指标"""
        with self._lock:
            self._events_published.clear()
            self._events_processed.clear()
            self._event_errors.clear()
            self._processing_times.clear()


class EventPublisher:
    """事件发布器"""

    def __init__(self, max_queue_size: int = 10000, enable_async: bool = True):
        self._subscriptions: Dict[EventType, List[EventSubscription]] = defaultdict(list)
        self._global_subscriptions: List[EventSubscription] = []
        self._lock = threading.RLock()
        self._subscription_counter = 0

        # 异步处理
        self._enable_async = enable_async
        self._event_queue = deque(maxlen=max_queue_size)
        self._processing_thread = None
        self._shutdown = False

        # 指标收集
        self.metrics = EventMetrics()

        if enable_async:
            self._start_processing_thread()

    def _start_processing_thread(self):
        """启动异步处理线程"""
        self._processing_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processing_thread.start()

    def _process_events(self):
        """异步处理事件"""
        while not self._shutdown:
            try:
                if self._event_queue:
                    event, subscription = self._event_queue.popleft()
                    self._handle_event_sync(event, subscription)
                else:
                    time.sleep(0.001)  # 避免忙等待
            except Exception as e:
                print(f"Event processing error: {e}")

    def subscribe(self, event_type: EventType, listener: Callable[[LifecycleEvent], None],
                  priority: int = 0, filter_func: Optional[Callable[[LifecycleEvent], bool]] = None,
                  weak_ref: bool = False) -> str:
        """订阅事件"""
        with self._lock:
            self._subscription_counter += 1
            subscription_id = f"sub_{self._subscription_counter}"

            subscription = EventSubscription(
                event_type=event_type,
                listener=listener,
                priority=priority,
                filter_func=filter_func,
                weak_ref=weak_ref,
                subscription_id=subscription_id
            )

            # 按优先级插入
            self._insert_subscription_sorted(event_type, subscription)
            self.metrics.increment_subscription()
            self.metrics.increment_listener()

            return subscription_id

    def subscribe_all(self, listener: Callable[[LifecycleEvent], None],
                      priority: int = 0, filter_func: Optional[Callable[[LifecycleEvent], bool]] = None,
                      weak_ref: bool = False) -> str:
        """订阅所有事件"""
        with self._lock:
            self._subscription_counter += 1
            subscription_id = f"global_{self._subscription_counter}"

            subscription = EventSubscription(
                event_type=EventType.CUSTOM,  # 使用CUSTOM表示全局订阅
                listener=listener,
                priority=priority,
                filter_func=filter_func,
                weak_ref=weak_ref,
                subscription_id=subscription_id
            )

            self._global_subscriptions.append(subscription)
            self._global_subscriptions.sort(key=lambda x: x.priority)

            self.metrics.increment_subscription()
            self.metrics.increment_listener()

            return subscription_id

    def _insert_subscription_sorted(self, event_type: EventType, subscription: EventSubscription):
        """按优先级插入订阅"""
        subscriptions = self._subscriptions[event_type]

        # 找到插入位置
        insert_index = len(subscriptions)
        for i, sub in enumerate(subscriptions):
            if subscription.priority < sub.priority:
                insert_index = i
                break

        subscriptions.insert(insert_index, subscription)

    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        with self._lock:
            # 检查特定事件订阅
            for event_type, subscriptions in self._subscriptions.items():
                for i, subscription in enumerate(subscriptions):
                    if subscription.subscription_id == subscription_id:
                        subscriptions.pop(i)
                        self.metrics.decrement_subscription()
                        self.metrics.decrement_listener()
                        return True

            # 检查全局订阅
            for i, subscription in enumerate(self._global_subscriptions):
                if subscription.subscription_id == subscription_id:
                    self._global_subscriptions.pop(i)
                    self.metrics.decrement_subscription()
                    self.metrics.decrement_listener()
                    return True

        return False

    def publish_event(self, event: LifecycleEvent) -> None:
        """发布事件"""
        if not self._enable_async:
            self._publish_event_sync(event)
        else:
            self._publish_event_async(event)

    def _publish_event_sync(self, event: LifecycleEvent) -> None:
        """同步发布事件"""
        self.metrics.record_event_published(event.event_type)

        # 处理特定事件类型的订阅
        for subscription in self._subscriptions[event.event_type][:]:  # 复制列表避免并发修改
            if self._should_process_subscription(subscription, event):
                self._handle_event_sync(event, subscription)

        # 处理全局订阅
        for subscription in self._global_subscriptions[:]:
            if self._should_process_subscription(subscription, event):
                self._handle_event_sync(event, subscription)

    def _publish_event_async(self, event: LifecycleEvent) -> None:
        """异步发布事件"""
        self.metrics.record_event_published(event.event_type)

        # 添加特定事件类型的订阅到队列
        for subscription in self._subscriptions[event.event_type][:]:
            if self._should_process_subscription(subscription, event):
                self._event_queue.append((event, subscription))

        # 添加全局订阅到队列
        for subscription in self._global_subscriptions[:]:
            if self._should_process_subscription(subscription, event):
                self._event_queue.append((event, subscription))

    def _should_process_subscription(self, subscription: EventSubscription, event: LifecycleEvent) -> bool:
        """判断是否应该处理订阅"""
        if subscription.filter_func:
            try:
                return subscription.filter_func(event)
            except Exception:
                return False
        return True

    def _handle_event_sync(self, event: LifecycleEvent, subscription: EventSubscription) -> None:
        """同步处理单个事件订阅"""
        start_time = time.time()

        try:
            # 检查弱引用
            if subscription.weak_ref:
                if hasattr(subscription.listener, '__self__'):
                    # 方法引用
                    if weakref.ref(subscription.listener.__self__)() is None:
                        return  # 对象已被回收
                else:
                    # 函数引用，不需要弱引用检查
                    pass

            subscription.listener(event)

        except Exception as e:
            self.metrics.record_event_error(event.event_type)
            # 记录错误但不中断其他监听器
            print(f"Event listener error for {event.event_type}: {e}")
        finally:
            processing_time = time.time() - start_time
            self.metrics.record_event_processed(event.event_type, processing_time)

    def get_subscription_count(self, event_type: Optional[EventType] = None) -> int:
        """获取订阅数量"""
        with self._lock:
            if event_type:
                return len(self._subscriptions[event_type])
            return len(self._global_subscriptions) + sum(len(subs) for subs in self._subscriptions.values())

    def get_event_types(self) -> List[EventType]:
        """获取已订阅的事件类型"""
        with self._lock:
            return list(self._subscriptions.keys())

    def shutdown(self):
        """关闭事件发布器"""
        if self._enable_async and self._processing_thread:
            self._shutdown = True
            self._processing_thread.join(timeout=5.0)


class LifecycleEventSystem:
    """生命周期事件系统"""

    def __init__(self, enable_async: bool = True, max_queue_size: int = 10000):
        self.publisher = EventPublisher(max_queue_size, enable_async)
        self._container_active = False

    def publish_bean_created(self, bean_name: str, bean_type: Type, instance: Any):
        """发布Bean创建事件"""
        event = LifecycleEvent(
            event_type=EventType.BEAN_CREATED,
            source=instance,
            bean_name=bean_name,
            bean_type=bean_type,
            data={'instance': instance}
        )
        self.publisher.publish_event(event)

    def publish_bean_destroyed(self, bean_name: str, bean_type: Type):
        """发布Bean销毁事件"""
        event = LifecycleEvent(
            event_type=EventType.BEAN_DESTROYED,
            source=None,
            bean_name=bean_name,
            bean_type=bean_type,
            data={'destroyed': True}
        )
        self.publisher.publish_event(event)

    def publish_bean_initialized(self, bean_name: str, bean_type: Type, instance: Any):
        """发布Bean初始化完成事件"""
        event = LifecycleEvent(
            event_type=EventType.BEAN_INITIALIZED,
            source=instance,
            bean_name=bean_name,
            bean_type=bean_type,
            data={'instance': instance}
        )
        self.publisher.publish_event(event)

    def publish_container_started(self, container_instance: Any):
        """发布容器启动事件"""
        self._container_active = True
        event = LifecycleEvent(
            event_type=EventType.CONTAINER_STARTED,
            source=container_instance,
            data={'active': True}
        )
        self.publisher.publish_event(event)

    def publish_container_stopped(self, container_instance: Any):
        """发布容器停止事件"""
        self._container_active = False
        event = LifecycleEvent(
            event_type=EventType.CONTAINER_STOPPED,
            source=container_instance,
            data={'active': False}
        )
        self.publisher.publish_event(event)

    def publish_container_refreshed(self, container_instance: Any, refreshed_beans: List[str]):
        """发布容器刷新事件"""
        event = LifecycleEvent(
            event_type=EventType.CONTAINER_REFRESHED,
            source=container_instance,
            data={'refreshed_beans': refreshed_beans}
        )
        self.publisher.publish_event(event)

    def publish_custom_event(self, source: Any, event_data: Dict[str, Any]):
        """发布自定义事件"""
        event = LifecycleEvent(
            event_type=EventType.CUSTOM,
            source=source,
            data=event_data
        )
        self.publisher.publish_event(event)

    def is_container_active(self) -> bool:
        """检查容器是否活跃"""
        return self._container_active

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取事件系统指标"""
        return {
            'publisher_metrics': self.publisher.metrics.get_metrics(),
            'container_active': self._container_active,
            'subscription_counts': {
                event_type.value: self.publisher.get_subscription_count(event_type)
                for event_type in self.publisher.get_event_types()
            }
        }

    def shutdown(self):
        """关闭事件系统"""
        self.publisher.shutdown()


# 全局生命周期事件系统实例
lifecycle_event_system = LifecycleEventSystem()
