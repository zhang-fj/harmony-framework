"""
Core scope module - re-exports from container for backward compatibility
"""

# 从container模块导入所有公共内容
from harmony.container.scope import (
    ScopeType,
    ScopeMetadata,
    ScopeManager,
    SingletonScopeManager,
    PrototypeScopeManager,
    RequestScopeManager,
    EnhancedScopeRegistry,
    enhanced_scope_registry
)

__all__ = [
    'ScopeType',
    'ScopeMetadata',
    'ScopeManager',
    'SingletonScopeManager',
    'PrototypeScopeManager',
    'RequestScopeManager',
    'EnhancedScopeRegistry',
    'enhanced_scope_registry'
]