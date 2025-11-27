"""
统一的作用域系统 - 支持多种作用域类型和生命周期管理
"""

import threading
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Callable


class ScopeType(Enum):
    """统一的作用域类型"""
    SINGLETON = "singleton"  # 单例 - 整个应用生命周期内唯一
    PROTOTYPE = "prototype"  # 原型 - 每次请求创建新实例
    REQUEST = "request"  # 请求 - 单个HTTP请求内唯一
    SESSION = "session"  # 会话 - 用户会话内唯一
    APPLICATION = "application"  # 应用 - Web应用上下文内唯一
    CUSTOM = "custom"  # 自定义 - 用户自定义作用域


@dataclass
class ScopeMetadata:
    """作用域元数据"""
    scope_type: ScopeType
    max_instances: Optional[int] = None
    ttl_seconds: Optional[float] = None
    cleanup_interval: float = 60.0
    auto_cleanup: bool = True
    description: str = ""
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class ScopeManager(ABC):
    """作用域管理器抽象基类"""

    @abstractmethod
    def get_instance(self, bean_name: str, factory: Callable) -> Any:
        """获取作用域内的实例"""
        pass

    @abstractmethod
    def remove_instance(self, bean_name: str) -> Optional[Any]:
        """移除作用域内的实例"""
        pass

    @abstractmethod
    def clear_all_instances(self) -> int:
        """清空所有实例"""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass


class SingletonScopeManager(ScopeManager):
    """单例作用域管理器"""

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get_instance(self, bean_name: str, factory: Callable) -> Any:
        with self._lock:
            if bean_name not in self._instances:
                self._instances[bean_name] = factory()
            return self._instances[bean_name]

    def remove_instance(self, bean_name: str) -> Optional[Any]:
        with self._lock:
            return self._instances.pop(bean_name, None)

    def clear_all_instances(self) -> int:
        with self._lock:
            count = len(self._instances)
            self._instances.clear()
            return count

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'type': 'singleton',
                'instance_count': len(self._instances),
                'instances': list(self._instances.keys())
            }


class PrototypeScopeManager(ScopeManager):
    """原型作用域管理器"""

    def __init__(self):
        self._instances: List[weakref.ref] = []
        self._lock = threading.RLock()

    def get_instance(self, bean_name: str, factory: Callable) -> Any:
        instance = factory()
        with self._lock:
            self._instances.append(weakref.ref(instance))
        return instance

    def remove_instance(self, bean_name: str) -> Optional[Any]:
        # 原型作用域不支持按名称移除
        return None

    def clear_all_instances(self) -> int:
        with self._lock:
            count = len([ref for ref in self._instances if ref() is not None])
            self._instances.clear()
            return count

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            active_instances = [ref for ref in self._instances if ref() is not None]
            return {
                'type': 'prototype',
                'active_instance_count': len(active_instances),
                'weak_ref_count': len(self._instances)
            }


class RequestScopeManager(ScopeManager):
    """请求作用域管理器"""

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get_instance(self, bean_name: str, factory: Callable) -> Any:
        with self._lock:
            if bean_name not in self._instances:
                self._instances[bean_name] = factory()
            return self._instances[bean_name]

    def remove_instance(self, bean_name: str) -> Optional[Any]:
        with self._lock:
            return self._instances.pop(bean_name, None)

    def clear_all_instances(self) -> int:
        with self._lock:
            count = len(self._instances)
            self._instances.clear()
            return count

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'type': 'request',
                'instance_count': len(self._instances),
                'instances': list(self._instances.keys())
            }

    def end_request(self):
        """结束请求，清理所有实例"""
        self.clear_all_instances()


class EnhancedScopeRegistry:
    """增强的作用域注册器"""

    def __init__(self):
        self._scope_managers: Dict[ScopeType, ScopeManager] = {}
        self._scope_metadata: Dict[ScopeType, ScopeMetadata] = {}
        self._custom_scopes: Dict[str, ScopeManager] = {}
        self._lock = threading.RLock()

        # 注册内置作用域
        self._register_builtin_scopes()

    def _register_builtin_scopes(self):
        """注册内置作用域"""
        self.register_scope(ScopeType.SINGLETON, SingletonScopeManager())
        self.register_scope(ScopeType.PROTOTYPE, PrototypeScopeManager())
        self.register_scope(ScopeType.REQUEST, RequestScopeManager())

        # 注册默认元数据
        self.register_metadata(ScopeType.SINGLETON, ScopeMetadata(
            scope_type=ScopeType.SINGLETON,
            description="应用单例作用域"
        ))
        self.register_metadata(ScopeType.PROTOTYPE, ScopeMetadata(
            scope_type=ScopeType.PROTOTYPE,
            description="原型作用域，每次请求创建新实例"
        ))
        self.register_metadata(ScopeType.REQUEST, ScopeMetadata(
            scope_type=ScopeType.REQUEST,
            ttl_seconds=30.0,
            cleanup_interval=30.0,
            description="HTTP请求作用域"
        ))

    def register_scope(self, scope_type: ScopeType, manager: ScopeManager):
        """注册作用域管理器"""
        with self._lock:
            self._scope_managers[scope_type] = manager

    def register_metadata(self, scope_type: ScopeType, metadata: ScopeMetadata):
        """注册作用域元数据"""
        with self._lock:
            self._scope_metadata[scope_type] = metadata

    def register_custom_scope(self, name: str, manager: ScopeManager):
        """注册自定义作用域"""
        with self._lock:
            self._custom_scopes[name] = manager

    def get_manager(self, scope_type: ScopeType) -> ScopeManager:
        """获取作用域管理器"""
        with self._lock:
            if scope_type == ScopeType.CUSTOM:
                raise ValueError("请使用 get_custom_manager 获取自定义作用域管理器")
            return self._scope_managers.get(scope_type)

    def get_custom_manager(self, name: str) -> Optional[ScopeManager]:
        """获取自定义作用域管理器"""
        with self._lock:
            return self._custom_scopes.get(name)

    def get_metadata(self, scope_type: ScopeType) -> Optional[ScopeMetadata]:
        """获取作用域元数据"""
        with self._lock:
            return self._scope_metadata.get(scope_type)

    def get_all_scope_statistics(self) -> Dict[str, Any]:
        """获取所有作用域的统计信息"""
        with self._lock:
            stats = {}
            for scope_type, manager in self._scope_managers.items():
                stats[scope_type.value] = manager.get_statistics()

            for name, manager in self._custom_scopes.items():
                stats[name] = manager.get_statistics()

            return stats

    def cleanup_all_scopes(self):
        """清理所有作用域"""
        with self._lock:
            for manager in self._scope_managers.values():
                if hasattr(manager, 'clear_all_instances'):
                    manager.clear_all_instances()

            for manager in self._custom_scopes.values():
                if hasattr(manager, 'clear_all_instances'):
                    manager.clear_all_instances()

    def get_available_scopes(self) -> List[str]:
        """获取所有可用的作用域类型"""
        with self._lock:
            scopes = [scope_type.value for scope_type in self._scope_managers.keys()]
            scopes.extend(self._custom_scopes.keys())
            return scopes


# 全局作用域注册器实例
enhanced_scope_registry = EnhancedScopeRegistry()
