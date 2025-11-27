"""
Harmony Framework - 轻量级Python依赖注入框架
"""

# 核心组件导入
from .core.application_context import ApplicationContext
from .core.bean_factory import BeanFactory
from .core.bean_definition import BeanDefinition
from .core.scope import ScopeType

# 注解系统导入
from .annotations.component import component, service, repository, controller, bean as bean_annotation
from .annotations.autowired import autowired_fields
from .annotations.lifecycle import PostConstruct, PreDestroy

# 容器系统导入
from .container.scope import ScopeManager, EnhancedScopeRegistry, enhanced_scope_registry
from .container.bean_creator import BeanCreator
from .container.dependency_resolver import DependencyResolver
from .container.injection_processor import InjectionProcessor

# 扫描系统导入
from .scanner.component_scanner import ComponentScanner, ClassPathScanningComponentScanner

# 配置系统导入
from .config.configuration import configuration, bean as config_bean
from .config.value import value, PropertyValueResolver
from .config.environment import Environment, EnvironmentManager, environment_manager

# AOP系统导入
from .aop.aop import JoinPoint, Aspect, BeforeAdvice, AfterAdvice, AspectManager

# 异常系统导入
from .exceptions.harmony_exceptions import (
    HarmonyException,
    NoSuchBeanDefinitionException,
    BeanCreationException,
    DependencyInjectionException,
    CircularDependencyException,
    BeanDefinitionStoreException,
    ConfigurationException,
    ScopeException,
    LifecycleException
)

# 工具系统导入
from .utils.logger import get_logger, HarmonyLogger, LogLevel
from .utils.reflection import get_class_methods, has_decorator

__version__ = "1.0.0"
__author__ = "Harmony Framework Team"
__description__ = "A Spring-like dependency injection framework for Python"

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__description__",

    # 核心组件
    "ApplicationContext",
    "BeanFactory",
    "BeanDefinition",
    "ScopeType",

    # 注解系统
    "component",
    "service",
    "repository",
    "controller",
    "bean_annotation",
    "autowired_fields",
    "PostConstruct",
    "PreDestroy",

    # 容器系统
    "ScopeManager",
    "EnhancedScopeRegistry",
    "enhanced_scope_registry",
    "BeanCreator",
    "DependencyResolver",
    "InjectionProcessor",

    # 扫描系统
    "ComponentScanner",
    "ClassPathScanningComponentScanner",

    # 配置系统
    "configuration",
    "config_bean",
    "value",
    "PropertyValueResolver",
    "Environment",
    "EnvironmentManager",
    "environment_manager",

    # AOP系统
    "JoinPoint",
    "Aspect",
    "BeforeAdvice",
    "AfterAdvice",
    "AspectManager",

    # 异常系统
    "HarmonyException",
    "NoSuchBeanDefinitionException",
    "BeanCreationException",
    "DependencyInjectionException",
    "CircularDependencyException",
    "BeanDefinitionStoreException",
    "ConfigurationException",
    "ScopeException",
    "LifecycleException",

    # 工具系统
    "get_logger",
    "HarmonyLogger",
    "LogLevel",
    "get_class_methods",
    "has_decorator"
]