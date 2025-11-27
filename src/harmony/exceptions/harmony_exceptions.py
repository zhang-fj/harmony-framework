import traceback
from typing import Optional, Dict, Any


class HarmonyException(Exception):
    """Harmony框架基础异常"""

    def __init__(self, message: str, cause: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.cause = cause
        self.context = context or {}
        self.timestamp = None

    def __str__(self) -> str:
        msg = super().__str__()
        if self.cause:
            msg += f" (Caused by: {type(self.cause).__name__}: {self.cause})"
        return msg

    def get_detailed_message(self) -> str:
        """获取详细错误信息"""
        msg = str(self)
        if self.context:
            msg += f"\nContext: {self.context}"
        if self.cause:
            msg += f"\nCause traceback:\n{''.join(traceback.format_tb(self.cause.__traceback__))}"
        return msg


class NoSuchBeanDefinitionException(HarmonyException):
    """Bean定义不存在异常"""

    def __init__(self, bean_name: str, suggested_names: Optional[list] = None,
                 available_types: Optional[list] = None, bean_type: Optional[type] = None):
        message = f"No bean named '{bean_name}' available"

        if suggested_names:
            message += f"\nDid you mean: {', '.join(suggested_names[:3])}?"

        if bean_type:
            if hasattr(bean_type, '__module__') and hasattr(bean_type, '__qualname__'):
                message += f"\nLooking for bean of type: {bean_type.__module__}.{bean_type.__qualname__}"
            else:
                message += f"\nLooking for bean of type: {bean_type}"

        if available_types:
            message += f"\nAvailable bean types: {len(available_types)} types registered"

        super().__init__(message)
        self.bean_name = bean_name
        self.suggested_names = suggested_names or []
        self.available_types = available_types or []
        self.bean_type = bean_type

    def get_suggestions(self) -> list:
        """获取修复建议"""
        suggestions = []

        if self.suggested_names:
            suggestions.extend([f"尝试使用: '{name}'" for name in self.suggested_names[:3]])

        if self.bean_type:
            suggestions.append(f"确保 {self.bean_type.__name__} 类有 @component 注解或等效标记")
            suggestions.append("检查类是否在扫描的包路径下")
            suggestions.append("验证 @componentscan 是否包含正确的包")

        suggestions.append("检查Bean名称拼写是否正确")
        suggestions.append("确认配置类已经正确扫描和注册")

        if '.' in self.bean_name:
            # 可能是类型查找而不是名称查找
            clean_name = self.bean_name.split('.')[-1]
            suggestions.append(f"如果按类型查找，请尝试使用 {clean_name} 类")

        return suggestions


class BeanCreationException(HarmonyException):
    """Bean创建异常"""

    def __init__(self, bean_name: str, message: str, cause: Optional[Exception] = None,
                 dependency_chain: Optional[list] = None, bean_type: Optional[type] = None,
                 context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if dependency_chain:
            context['dependency_chain'] = dependency_chain
            chain_str = " -> ".join(dependency_chain + [bean_name])
            detailed_message = f"Error creating bean '{bean_name}' in dependency chain: {chain_str}. {message}"
        else:
            detailed_message = f"Error creating bean '{bean_name}': {message}"

        if bean_type:
            context['bean_type'] = f"{bean_type.__module__}.{bean_type.__qualname__}"

        super().__init__(detailed_message, cause, context)
        self.bean_name = bean_name
        self.dependency_chain = dependency_chain or []
        self.bean_type = bean_type

    def get_suggestions(self) -> list:
        """获取修复建议"""
        suggestions = []

        if "circular dependency" in str(self).lower():
            suggestions.append("检查是否存在循环依赖，尝试使用 @Lazy 注解延迟初始化")
            suggestions.append("重新设计组件依赖关系以避免循环引用")

        if "multiple candidates" in str(self).lower():
            suggestions.append("使用 @qualifier 注解指定具体的Bean")
            suggestions.append("使用 @primary 注解标记首选的Bean")

        if self.bean_type and not self.dependency_chain:
            suggestions.append(f"确保 {self.bean_type.__name__} 类型有对应的Bean定义")
            suggestions.append("检查是否缺少 @component 或相关注解")

        if self.cause and "ImportError" in str(type(self.cause)):
            suggestions.append("检查模块导入路径是否正确")
            suggestions.append("确保所有依赖包都已正确安装")

        return suggestions


class DependencyInjectionException(HarmonyException):
    """依赖注入异常"""

    def __init__(self, message: str, dependency_name: Optional[str] = None,
                 bean_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.dependency_name = dependency_name
        self.bean_name = bean_name


class CircularDependencyException(HarmonyException):
    """循环依赖异常"""

    def __init__(self, bean_name: str, dependency_chain: list):
        chain_str = " -> ".join(dependency_chain + [bean_name])
        message = f"Circular dependency detected: {chain_str}"
        super().__init__(message)
        self.bean_name = bean_name
        self.dependency_chain = dependency_chain


class BeanDefinitionStoreException(HarmonyException):
    """Bean定义存储异常"""

    def __init__(self, message: str, bean_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.bean_name = bean_name


class ConfigurationException(HarmonyException):
    """配置异常"""

    def __init__(self, message: str, config_key: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.config_key = config_key


class ScopeException(HarmonyException):
    """作用域异常"""

    def __init__(self, message: str, scope_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.scope_name = scope_name


class LifecycleException(HarmonyException):
    """生命周期异常"""

    def __init__(self, message: str, phase: Optional[str] = None, bean_name: Optional[str] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.phase = phase
        self.bean_name = bean_name
