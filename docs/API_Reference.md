# Harmony Framework API 参考文档

## 目录

- [核心接口](#核心接口)
- [注解列表](#注解列表)
- [异常类](#异常类)
- [配置类](#配置类)
- [工具类](#工具类)
- [扩展接口](#扩展接口)

## 核心接口

### ApplicationContext

应用上下文是 Harmony Framework 的核心接口，提供了完整的 Bean 管理功能。

```python
class ApplicationContext:
    """应用上下文 - 核心IoC容器"""

    def __init__(self):
        """初始化应用上下文"""

    def register_bean(
        self,
        bean_type: Type,
        bean_name: Optional[str] = None,
        scope: str = ScopeType.SINGLETON.value,
        constructor_args: List[Any] = None,
        primary: bool = False,
        lazy: bool = False
    ) -> None:
        """
        注册Bean到容器

        Args:
            bean_type: Bean类型
            bean_name: Bean名称，默认为类名
            scope: 作用域，默认为单例
            constructor_args: 构造器参数
            primary: 是否为主要Bean
            lazy: 是否延迟初始化
        """

    def get_bean(self, bean_name: str) -> Any:
        """
        根据名称获取Bean实例

        Args:
            bean_name: Bean名称

        Returns:
            Bean实例

        Raises:
            NoSuchBeanDefinitionException: Bean不存在
        """

    def get_bean_by_type(self, bean_type: Type, qualifier: Optional[str] = None) -> Any:
        """
        根据类型获取Bean实例

        Args:
            bean_type: Bean类型
            qualifier: 限定符（当有多个同类型Bean时使用）

        Returns:
            Bean实例
        """

    def get_bean_names_for_type(self, bean_type: Type) -> List[str]:
        """
        获取指定类型的所有Bean名称

        Args:
            bean_type: Bean类型

        Returns:
            Bean名称列表
        """

    def contains_bean(self, bean_name: str) -> bool:
        """
        检查是否包含指定名称的Bean

        Args:
            bean_name: Bean名称

        Returns:
            是否包含
        """

    def get_bean_names(self) -> List[str]:
        """
        获取所有Bean名称

        Returns:
            Bean名称列表
        """

    def component_scan(
        self,
        *base_packages: str,
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None,
        filters: List[callable] = None
    ) -> None:
        """
        配置组件扫描

        Args:
            *base_packages: 基础包名
            exclude_patterns: 排除模式列表
            include_patterns: 包含模式列表
            filters: 自定义过滤器列表
        """

    def register_classes(self, *classes: Type) -> None:
        """
        注册指定类进行扫描

        Args:
            *classes: 要扫描的类
        """

    def refresh(self) -> None:
        """刷新应用上下文 - 执行扫描和Bean注册"""

    def add_property_source(self, source: dict) -> None:
        """
        添加属性源

        Args:
            source: 属性字典
        """

    def load_properties_from_file(self, file_path: str) -> None:
        """
        从文件加载属性

        Args:
            file_path: 属性文件路径
        """

    def register_configuration(self, config_class: Type) -> None:
        """
        注册配置类

        Args:
            config_class: 配置类
        """

    def close(self) -> None:
        """关闭应用上下文"""

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()
```

### BeanFactory

Bean工厂接口，负责Bean的创建和管理。

```python
class BeanFactory:
    """Bean工厂 - 负责Bean实例的创建和管理"""

    def __init__(self):
        """初始化Bean工厂"""

    def register_bean_definition(self, bean_definition: BeanDefinition) -> None:
        """
        注册Bean定义

        Args:
            bean_definition: Bean定义对象
        """

    def get_bean_definition(self, bean_name: str) -> BeanDefinition:
        """
        获取Bean定义

        Args:
            bean_name: Bean名称

        Returns:
            Bean定义对象
        """

    def contains_bean_definition(self, bean_name: str) -> bool:
        """
        检查是否包含Bean定义

        Args:
            bean_name: Bean名称

        Returns:
            是否包含
        """

    def get_bean(self, bean_name: str) -> Any:
        """
        获取Bean实例

        Args:
            bean_name: Bean名称

        Returns:
            Bean实例
        """

    def pre_instantiate_singletons(self) -> None:
        """预实例化所有非延迟的单例Bean"""

    def destroy_singletons(self) -> None:
        """销毁所有单例Bean"""

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取工厂统计信息

        Returns:
            统计信息字典
        """
```

### BeanDefinition

Bean定义类，包含Bean的完整元数据。

```python
@dataclass
class BeanDefinition:
    """Bean定义 - 包含Bean的完整元数据"""

    bean_type: Type
    bean_name: str
    scope: ScopeType = ScopeType.SINGLETON
    primary: bool = False
    lazy_init: bool = False
    factory_method: Optional[callable] = None
    init_method: Optional[str] = None
    destroy_method: Optional[str] = None
    constructor_args: List[Any] = field(default_factory=list)

    def add_constructor_arg(self, param_type: Type, param_value: Any, required: bool = True) -> None:
        """
        添加构造器参数

        Args:
            param_type: 参数类型
            param_value: 参数值
            required: 是否必需
        """

    def get_constructor_args(self) -> List[Tuple[Type, Any, bool]]:
        """
        获取构造器参数列表

        Returns:
            构造器参数列表 (类型, 值, 是否必需)
        """

    def is_singleton(self) -> bool:
        """是否为单例作用域"""
        return self.scope == ScopeType.SINGLETON

    def is_prototype(self) -> bool:
        """是否为原型作用域"""
        return self.scope == ScopeType.PROTOTYPE
```

## 注解列表

### 组件注解

#### @component

通用组件注解，标记一个类为Spring组件。

```python
def component(
    bean_name: Optional[str] = None,
    scope=ScopeType.SINGLETON,
    primary: bool = False,
    lazy: bool = False
):
    """
    组件注解

    Args:
        bean_name: Bean名称
        scope: 作用域
        primary: 是否为主要Bean
        lazy: 是否延迟初始化
    """

    def decorator(cls):
        # 设置组件元数据
        cls.__harmony_component_metadata__ = {
            'bean_name': bean_name,
            'scope': scope,
            'primary': primary,
            'lazy': lazy
        }
        cls.__harmony_component__ = True
        return cls

    return decorator
```

**使用示例:**
```python
@component(bean_name="utilService", scope=ScopeType.SINGLETON.value)
class UtilService:
    def format_string(self, text: str) -> str:
        return text.upper()
```

#### @service

服务层组件注解。

```python
def service(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """
    服务层注解

    Args:
        bean_name: Bean名称
        scope: 作用域
    """

    def decorator(cls):
        cls.__harmony_service_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_service__ = True
        return cls

    return decorator
```

**使用示例:**
```python
@service("userService")
class UserService:
    def create_user(self, name: str) -> str:
        return f"用户 {name} 创建成功"
```

#### @repository

数据访问层组件注解。

```python
def repository(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """数据访问层注解"""

    def decorator(cls):
        cls.__harmony_repository_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_repository__ = True
        return cls

    return decorator
```

**使用示例:**
```python
@Repository("userRepository")
class UserRepository:
    def find_by_id(self, user_id: int) -> Dict:
        return {"id": user_id, "name": f"User{user_id}"}
```

#### @controller

控制层组件注解。

```python
def controller(bean_name: Optional[str] = None, scope=ScopeType.SINGLETON):
    """控制层注解"""

    def decorator(cls):
        cls.__harmony_controller_metadata__ = {
            'bean_name': bean_name,
            'scope': scope
        }
        cls.__harmony_controller__ = True
        return cls

    return decorator
```

**使用示例:**
```python
@Controller("userController")
class UserController:
    def handle_request(self, path: str) -> str:
        return f"处理请求: {path}"
```

### 依赖注入注解

#### @constructor_autowired

构造器自动注入注解。

```python
def constructor_autowired(cls):
    """
    构造器自动注入注解
    标记需要构造器注入
    """
    cls.__harmony_constructor_autowired__ = True
    return cls
```

**使用示例:**
```python
@constructor_autowired
class OrderService:
    def __init__(self, user_repository: UserRepository, product_repository: ProductRepository):
        self.user_repository = user_repository
        self.product_repository = product_repository
```

#### @bean

手动Bean定义注解。

```python
def bean(
    bean_name: Optional[str] = None,
    scope=ScopeType.SINGLETON,
    primary: bool = False,
    lazy: bool = False,
    init_method: Optional[str] = None,
    destroy_method: Optional[str] = None
):
    """
    通用Bean注解

    Args:
        bean_name: Bean名称
        scope: 作用域
        primary: 是否为主要Bean
        lazy: 是否延迟初始化
        init_method: 初始化方法名
        destroy_method: 销毁方法名
    """

    def decorator(cls):
        cls.__harmony_bean__ = {
            'bean_name': bean_name,
            'scope': scope,
            'primary': primary,
            'lazy': lazy,
            'init_method': init_method,
            'destroy_method': destroy_method
        }
        return cls

    return decorator
```

**使用示例:**
```python
@Configuration
class DatabaseConfig:
    @bean("dataSource")
    def create_data_source(self):
        return DataSource("jdbc:mysql://localhost:3306/test")
```

### 配置注解

#### @configuration

配置类注解。

```python
def configuration(cls):
    """配置类注解"""
    cls.__harmony_configuration__ = True
    return cls
```

**使用示例:**
```python
@configuration
class AppConfig:
    @bean("appProperties")
    def app_properties(self):
        return {"name": "MyApp", "version": "1.0.0"}
```

#### @ConfigurationProperties

配置属性注解。

```python
def ConfigurationProperties(prefix: str = ""):
    """
    配置属性注解

    Args:
        prefix: 配置前缀
    """

    def decorator(cls):
        cls.__harmony_configuration_properties__ = prefix
        return cls

    return decorator
```

**使用示例:**
```python
@ConfigurationProperties(prefix="app.database")
class DatabaseConfig:
    def __init__(self):
        self.url = None
        self.username = None
        self.password = None
        self.pool_size = 10
```

#### @Profile

环境配置注解。

```python
def profile(*profiles: str):
    """
    环境配置注解

    Args:
        *profiles: 环境名称列表
    """

    def decorator(cls):
        cls.__harmony_profiles__ = profiles
        return cls

    return decorator
```

**使用示例:**
```python
@profile("development")
class DevConfig:
    @bean
    def data_source(self):
        return DataSource("jdbc:h2:mem:dev")

@profile("production")
class ProdConfig:
    @bean
    def data_source(self):
        return DataSource("jdbc:mysql://prod-db:3306/app")
```

## 异常类

### 基础异常

#### HarmonyException

Harmony Framework 基础异常类。

```python
class HarmonyException(Exception):
    """Harmony Framework 基础异常"""

    def __init__(self, message: str, cause: Exception = None):
        """
        初始化异常

        Args:
            message: 异常消息
            cause: 原因异常
        """
        super().__init__(message)
        self.cause = cause
```

### Bean相关异常

#### NoSuchBeanDefinitionException

Bean定义不存在异常。

```python
class NoSuchBeanDefinitionException(HarmonyException):
    """Bean定义不存在异常"""

    def __init__(self, bean_name: str):
        super().__init__(f"No bean named '{bean_name}' is defined")
        self.bean_name = bean_name
```

#### BeanCreationException

Bean创建异常。

```python
class BeanCreationException(HarmonyException):
    """Bean创建异常"""

    def __init__(self, bean_name: str, cause: Exception = None):
        super().__init__(f"Error creating bean '{bean_name}'", cause)
        self.bean_name = bean_name
```

#### BeanNotOfRequiredTypeException

Bean类型不匹配异常。

```python
class BeanNotOfRequiredTypeException(HarmonyException):
    """Bean类型不匹配异常"""

    def __init__(self, bean_name: str, required_type: Type, actual_type: Type):
        super().__init__(
            f"Bean named '{bean_name}' is expected to be of type '{required_type}' "
            f"but was actually of type '{actual_type}'"
        )
        self.bean_name = bean_name
        self.required_type = required_type
        self.actual_type = actual_type
```

#### CircularDependencyException

循环依赖异常。

```python
class CircularDependencyException(HarmonyException):
    """循环依赖异常"""

    def __init__(self, dependency_chain: List[str]):
        chain_str = " -> ".join(dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")
        self.dependency_chain = dependency_chain
```

## 配置类

### ScopeType

作用域类型枚举。

```python
class ScopeType(Enum):
    """作用域类型枚举"""

    SINGLETON = "singleton"  # 单例作用域
    PROTOTYPE = "prototype"  # 原型作用域
    REQUEST = "request"     # 请求作用域
    SESSION = "session"     # 会话作用域
```

### Environment

环境配置类。

```python
class Environment:
    """环境配置管理"""

    def __init__(self):
        self.active_profiles = ["default"]
        self.property_sources = []

    def get_active_profile(self) -> str:
        """获取当前激活的环境"""
        return self.active_profiles[0] if self.active_profiles else "default"

    def set_active_profiles(self, *profiles: str) -> None:
        """设置激活的环境"""
        self.active_profiles = list(profiles)

    def is_development(self) -> bool:
        """是否为开发环境"""
        return "development" in self.active_profiles

    def is_production(self) -> bool:
        """是否为生产环境"""
        return "production" in self.active_profiles

    def is_test(self) -> bool:
        """是否为测试环境"""
        return "test" in self.active_profiles

    def get_property(self, key: str, default: Any = None, type: Type = str) -> Any:
        """
        获取配置属性

        Args:
            key: 属性键
            default: 默认值
            type: 类型

        Returns:
            属性值
        """

    def contains_property(self, key: str) -> bool:
        """检查是否包含指定属性"""
```

### PropertyValueResolver

属性值解析器。

```python
class PropertyValueResolver:
    """属性值解析器"""

    def __init__(self):
        self.properties = {}

    def add_properties(self, properties: dict) -> None:
        """添加属性"""
        self.properties.update(properties)

    def get_property(self, key: str, default: Any = None, type: Type = str) -> Any:
        """获取属性值"""
        value = self.properties.get(key, default)

        if type and value is not None:
            try:
                if type == bool:
                    return str(value).lower() in ('true', '1', 'yes', 'on')
                elif type == int:
                    return int(value)
                elif type == float:
                    return float(value)
                else:
                    return type(value)
            except (ValueError, TypeError):
                return default

        return value

    def load_from_file(self, file_path: str) -> None:
        """从文件加载属性"""

    def resolve_placeholders(self, text: str) -> str:
        """解析占位符 ${}"""
```

## 工具类

### ComponentScanner

组件扫描器。

```python
class ComponentScanner:
    """组件扫描器"""

    def __init__(self):
        self.exclude_patterns = []
        self.include_patterns = []
        self.filters = []

    def add_exclude_pattern(self, pattern: str) -> None:
        """添加排除模式"""
        self.exclude_patterns.append(pattern)

    def add_include_pattern(self, pattern: str) -> None:
        """添加包含模式"""
        self.include_patterns.append(pattern)

    def add_filter(self, filter_func: callable) -> None:
        """添加自定义过滤器"""
        self.filters.append(filter_func)

    def scan_packages(self, *base_packages: str) -> List[BeanDefinition]:
        """
        扫描指定包

        Args:
            *base_packages: 基础包名

        Returns:
            扫描到的Bean定义列表
        """

    def scan_classes(self, *classes: Type) -> List[BeanDefinition]:
        """
        扫描指定类

        Args:
            *classes: 要扫描的类

        Returns:
            扫描到的Bean定义列表
        """

    def get_scanned_count(self) -> Dict[str, int]:
        """获取扫描统计信息"""
```

### ConfigurationPropertiesBinder

配置属性绑定器。

```python
class ConfigurationPropertiesBinder:
    """配置属性绑定器"""

    def __init__(self, value_resolver: PropertyValueResolver):
        self.value_resolver = value_resolver

    def bind_properties(self, config_class: Type) -> Any:
        """
        绑定属性到配置类

        Args:
            config_class: 配置类

        Returns:
            配置实例
        """

    def collect_bean_definitions(self, config_instance: Any) -> List[Dict]:
        """
        收集配置类中定义的Bean

        Args:
            config_instance: 配置实例

        Returns:
            Bean定义列表
        """
```

## 扩展接口

### BeanPostProcessor

Bean后置处理器接口。

```python
class BeanPostProcessor:
    """Bean后置处理器接口"""

    def post_process_before_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        初始化前处理

        Args:
            bean: Bean实例
            bean_name: Bean名称

        Returns:
            处理后的Bean实例
        """
        return bean

    def post_process_after_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        初始化后处理

        Args:
            bean: Bean实例
            bean_name: Bean名称

        Returns:
            处理后的Bean实例
        """
        return bean
```

### BeanFactoryPostProcessor

Bean工厂后置处理器接口。

```python
class BeanFactoryPostProcessor:
    """Bean工厂后置处理器接口"""

    def post_process_bean_factory(self, bean_factory: BeanFactory) -> None:
        """
        后置处理Bean工厂

        Args:
            bean_factory: Bean工厂实例
        """
        pass
```

### ApplicationContextAware

应用上下文感知接口。

```python
class ApplicationContextAware:
    """应用上下文感知接口"""

    def set_application_context(self, application_context: ApplicationContext) -> None:
        """
        设置应用上下文

        Args:
            application_context: 应用上下文实例
        """
        pass
```

### DisposableBean

可销毁Bean接口。

```python
class DisposableBean:
    """可销毁Bean接口"""

    def destroy(self) -> None:
        """销毁方法"""
        pass
```

### InitializingBean

可初始化Bean接口。

```python
class InitializingBean:
    """可初始化Bean接口"""

    def after_properties_set(self) -> None:
        """属性设置后的初始化方法"""
        pass
```

## 使用示例

### 完整的应用示例

```python
from harmony.core.application_context import ApplicationContext
from harmony.annotations.component import service, repository, configuration, bean
from harmony.core.scope import ScopeType

# 模型类
class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

# 仓库层
@Repository("userRepository")
class UserRepository:
    def find_by_id(self, user_id: int) -> User:
        return User(user_id, f"User{user_id}")

    def save(self, user: User) -> User:
        print(f"保存用户: {user.name}")
        return user

# 服务层
@service("userService")
class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user(self, user_id: int) -> User:
        return self.user_repository.find_by_id(user_id)

    def create_user(self, name: str) -> User:
        user = User(0, name)
        return self.user_repository.save(user)

# 配置类
@configuration
class AppConfig:
    @bean("appProperties")
    def app_properties(self):
        return {
            "app.name": "Harmony Demo",
            "app.version": "1.0.0"
        }

# 应用入口
def main():
    context = ApplicationContext()

    try:
        # 注册配置
        context.register_configuration(AppConfig)

        # 扫描组件
        context.component_scan("com.example")
        context.refresh()

        # 获取和使用Bean
        user_service = context.get_bean("userService")

        # 创建用户
        user = user_service.create_user("张三")
        print(f"创建用户: {user.name}")

        # 查询用户
        found_user = user_service.get_user(user.id)
        print(f"查询用户: {found_user.name}")

        # 获取配置
        app_props = context.get_bean("appProperties")
        print(f"应用信息: {app_props}")

    finally:
        context.close()

if __name__ == "__main__":
    main()
```

---

## 版本信息

- **当前版本**: 1.0.0
- **Python版本**: 3.7+
- **最后更新**: 2024年

更多信息请参考 [用户手册](./Harmony_Framework_User_Manual.md) 和 [快速入门指南](./Quick_Start_Guide.md)。