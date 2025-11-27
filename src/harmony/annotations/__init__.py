"""
Harmony注解系统 - 提供依赖注入和组件扫描的注解
"""

from .component import (
    component,
    service,
    repository,
    controller,
    constructor_autowired,
    bean,
    create_bean_definition
)
from .autowired import autowired_fields
from .lifecycle import (
    PostConstruct,
    PreDestroy,
    LifecyclePhase,
    LifecycleCallback,
    LifecycleManager,
    SmartInitializingSingleton,
    DisposableBean,
    ApplicationContextAware
)

__all__ = [
    # 组件注解
    "component",
    "service",
    "repository",
    "controller",
    "constructor_autowired",
    "bean",
    "create_bean_definition",

    # 自动装配注解
    "autowired_fields",

    # 生命周期注解
    "PostConstruct",
    "PreDestroy",
    "LifecyclePhase",
    "LifecycleCallback",
    "LifecycleManager",
    "SmartInitializingSingleton",
    "DisposableBean",
    "ApplicationContextAware"
]