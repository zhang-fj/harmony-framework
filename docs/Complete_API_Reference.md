# Harmony Framework 完整API参考

## 📖 目录

- [核心API](#核心api)
- [注解API](#注解api)
- [配置API](#配置api)
- [AOP API](#aop-api)
- [扩展API](#扩展api)
- [工具API](#工具api)
- [异常API](#异常api)

## 核心API

### ApplicationContext

应用上下文是 Harmony Framework 的核心接口，提供了完整的Bean管理功能。

#### 构造函数

```python
ApplicationContext(bean_factory: BeanFactory = None)
```

**参数:**
- `bean_factory`: 可选的Bean工厂实例，默认使用DefaultBeanFactory

#### 主要方法

##### Bean注册和管理

```python
def register_bean(self, bean_type: Type, bean_name: str, **kwargs) -> None
```
注册Bean定义到容器中。

**参数:**
- `bean_type`: Bean的类型
- `bean_name`: Bean的名称
- `**kwargs`: 额外参数，包括scope、primary、lazy等

```python
def register_bean_instance(self, bean_type: Type, bean_name: str, instance: Any) -> None
```
注册已存在的Bean实例。

```python
def get_bean(self, bean_name: str) -> Any
```
根据Bean名称获取Bean实例。

```python
def get_bean_by_type(self, bean_type: Type, qualifier: str = None) -> Any
```
根据类型获取Bean实例。

**参数:**
- `bean_type`: Bean的类型
- `qualifier`: 可选的限定符，用于区分同类型的多个Bean

```python
def get_bean_names_for_type(self, bean_type: Type) -> List[str]
```
获取指定类型的所有Bean名称。

##### 组件扫描

```python
def component_scan(self, *base_packages: str, **kwargs) -> None
```
配置组件扫描。

**参数:**
- `base_packages`: 要扫描的基础包名
- `**kwargs`: 额外参数，包括exclude_patterns、include_patterns、filters等

```python
def refresh(self) -> None
```
刷新应用上下文，执行组件扫描和Bean初始化。

##### 配置管理

```python
def add_property_source(self, source: dict) -> None
```
添加属性源。

```python
def load_properties_from_file(self, file_path: str) -> None
```
从文件加载属性配置。

```python
def get_property(self, key: str, default_value: Any = None) -> Any
```
获取配置属性值。

##### 生命周期管理

```python
def close(self) -> None
```
关闭应用上下文，销毁所有Bean。

```python
def is_active(self) -> bool
```
检查应用上下文是否处于活跃状态。

#### 使用示例

```python
from harmony.core.application_context import ApplicationContext

# 创建应用上下文
context = ApplicationContext()

# 注册Bean
context.register_bean(UserService, "userService")

# 组件扫描
context.component_scan("com.example.services")

# 刷新上下文
context.refresh()

# 获取Bean
user_service = context.get_bean("userService")

# 关闭上下文
context.close()
```

### BeanFactory

Bean工厂接口，定义了Bean的基本操作。

#### 方法

```python
def register_bean_definition(self, bean_definition: BeanDefinition) -> None
```
注册Bean定义。

```python
def get_bean_definition(self, bean_name: str) -> BeanDefinition
```
获取Bean定义。

```python
def contains_bean_definition(self, bean_name: str) -> bool
```
检查是否包含Bean定义。

```python
def get_bean(self, bean_name: str) -> Any
```
获取Bean实例。

```python
def pre_instantiate_singletons(self) -> None
```
预实例化所有单例Bean。

```python
def destroy_singletons(self) -> None
```
销毁所有单例Bean。

```python
def get_statistics(self) -> Dict[str, Any]
```
获取Bean工厂统计信息。

### BeanDefinition

Bean定义类，包含Bean的完整元数据。

#### 属性

```python
class BeanDefinition:
    bean_type: Type                    # Bean类型
    bean_name: str                     # Bean名称
    scope: ScopeType = ScopeType.SINGLETON  # 作用域
    primary: bool = False              # 是否为主要Bean
    lazy_init: bool = False            # 是否延迟初始化
    constructor_args: List[Any] = []   # 构造器参数
    property_values: Dict[str, Any] = {}  # 属性值
    factory_method: str = None         # 工厂方法名
    factory_bean: str = None           # 工厂Bean名
    init_method: str = None            # 初始化方法
    destroy_method: str = None         # 销毁方法
    depends_on: List[str] = []         # 依赖的Bean
    autowire_mode: AutowireMode = AutowireMode.NONE  # 自动装配模式
```

#### 方法

```python
def is_singleton(self) -> bool
```
检查是否为单例作用域。

```python
def is_prototype(self) -> bool
```
检查是否为原型作用域。

```python
def get_dependency_names(self) -> List[str]
```
获取依赖的Bean名称列表。

### ScopeType

作用域类型枚举。

```python
class ScopeType(Enum):
    SINGLETON = "singleton"    # 单例作用域
    PROTOTYPE = "prototype"    # 原型作用域
    REQUEST = "request"        # 请求作用域
    SESSION = "session"        # 会话作用域
```

## 注解API

### @Component

通用组件注解。

```python
@component(bean_name=None, scope=ScopeType.SINGLETON, primary=False, lazy=False)
```

**参数:**
- `bean_name`: Bean名称，默认使用类名小驼峰形式
- `scope`: 作用域，默认为单例
- `primary`: 是否为主要Bean，默认为False
- `lazy`: 是否延迟初始化，默认为False

```python
from harmony.annotations.component import component

@component(bean_name="myComponent", scope=ScopeType.PROTOTYPE)
class MyComponent:
    pass
```

### @Service

服务层组件注解。

```python
@service(bean_name=None, scope=ScopeType.SINGLETON)
```

```python
from harmony.annotations.component import service

@service("userService")
class UserService:
    pass
```

### @Repository

数据访问层组件注解。

```python
@Repository(bean_name=None, scope=ScopeType.SINGLETON)
```

```python
from harmony.annotations.component import Repository

@Repository("userRepository")
class UserRepository:
    pass
```

### @Controller

控制层组件注解。

```python
@Controller(bean_name=None, scope=ScopeType.SINGLETON)
```

```python
from harmony.annotations.component import Controller

@Controller("userController")
class UserController:
    pass
```

### @Autowired

自动装配注解。

```python
@constructor_autowired  # 构造器注入
@autowired             # 字段注入
```

```python
from harmony.annotations.component import component, constructor_autowired

@component
class DatabaseService:
    pass

@constructor_autowired
class UserService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
```

### @Bean

Bean定义注解，用于配置类中。

```python
@bean(bean_name=None, scope=ScopeType.SINGLETON, primary=False, lazy=False)
```

```python
from harmony.annotations.bean import bean
from harmony.annotations.component import configuration

@configuration
class AppConfig:
    @bean
    def data_source(self):
        return DataSource("jdbc:mysql://localhost:3306/test")

    @bean(name="redisClient")
    def redis_client(self):
        return RedisClient()
```

### @Configuration

配置类注解。

```python
from harmony.annotations.component import configuration

@configuration
class DatabaseConfig:
    @bean
    def data_source(self):
        return DataSource()
```

### @ConfigurationProperties

配置属性绑定注解。

```python
@ConfigurationProperties(prefix="app.database")
class DatabaseConfig:
    def __init__(self):
        self.url = None
        self.username = None
        self.password = None
```

### @Value

属性值注入注解。

```python
from harmony.annotations.value import Value

@component
class MyService:
    def __init__(self, timeout: Value[int]):
        self.timeout = timeout.get()  # 从配置文件获取值
```

### 生命周期注解

```python
from harmony.annotations.lifecycle import PostConstruct, PreDestroy

@component
class MyService:
    @PostConstruct
    def init(self):
        print("服务初始化")

    @PreDestroy
    def cleanup(self):
        print("服务清理")
```

### 条件注解

```python
from harmony.annotations.condition import ConditionalOnProperty, ConditionalOnClass

@ConditionalOnProperty(name="app.cache.enabled", havingValue="true")
@ConditionalOnClass("redis.Redis")
class RedisCacheService:
    pass
```

## 配置API

### Environment

环境配置类。

```python
from harmony.config.environment import Environment

env = Environment()

# 设置活动环境
env.set_active_profiles("development")

# 获取活动环境
profile = env.get_active_profile()

# 检查环境
if env.is_development():
    print("开发环境")
elif env.is_production():
    print("生产环境")
```

### ConfigurationProperties

配置属性类。

```python
from harmony.config.configuration import ConfigurationProperties

@ConfigurationProperties(prefix="app")
class AppConfig:
    def __init__(self):
        self.name = None
        self.version = None
        self.debug = False
```

### PropertySource

属性源接口。

```python
from harmony.config.property_source import PropertySource, MapPropertySource

# 创建Map属性源
properties = {
    "database.url": "jdbc:mysql://localhost:3306/test",
    "database.username": "admin"
}
property_source = MapPropertySource("config", properties)

# 添加到环境
env.add_property_source(property_source)
```

### @Profile

环境配置注解。

```python
from harmony.annotations.profile import Profile

@Profile("development")
class DevDatabaseConfig:
    @bean
    def data_source(self):
        return DataSource("jdbc:h2:mem:dev")

@Profile("production")
class ProdDatabaseConfig:
    @bean
    def data_source(self):
        return DataSource("jdbc:mysql://prod-db:3306/app")
```

## AOP API

### AspectManager

切面管理器。

```python
from harmony.aop.aop import AspectManager

# 创建切面管理器
aspect_manager = AspectManager()

# 创建切面
logging_aspect = aspect_manager.create_aspect("logging")

# 添加切点
@logging_aspect.before("execution(* com.example.service.*.*(..))")
def log_before(join_point: JoinPoint):
    print(f"执行方法: {join_point.method_name}")
```

### Aspect

切面类。

```python
from harmony.aop.aop import Aspect, Before, After, Around

# 创建切面
aspect = Aspect("logging")

# 定义通知
@aspect.before("execution(* com.example.service.*.*(..))")
def before_advice(join_point: JoinPoint):
    print(f"前置通知: {join_point.method_name}")

@aspect.after("execution(* com.example.service.*.*(..))")
def after_advice(join_point: JoinPoint, result, exception):
    print(f"后置通知: {join_point.method_name}")

@aspect.around("execution(* com.example.service.*.*(..))")
def around_advice(invocation: MethodInvocation):
    print(f"环绕通知开始: {invocation.join_point.method_name}")
    result = invocation.proceed()
    print(f"环绕通知结束: {invocation.join_point.method_name}")
    return result
```

### JoinPoint

连接点类。

```python
from harmony.aop.aop import JoinPoint

# JoinPoint 属性
join_point.target          # 目标对象
join_point.method_name     # 方法名
join_point.args            # 方法参数
join_point.kwargs          # 关键字参数
join_point.join_point_type # 连接点类型
```

### MethodInvocation

方法调用信息类。

```python
from harmony.aop.aop import MethodInvocation

# MethodInvocation 属性
invocation.join_point       # 连接点
invocation.proceed()        # 执行原方法
invocation.returned_value   # 返回值
invocation.exception        # 异常
invocation.execution_time   # 执行时间
```

### 切点表达式

支持的切点表达式格式：

```python
# 执行所有方法
"execution(* *.*(..))"

# 执行指定类的所有方法
"execution(* com.example.service.*.*(..))"

# 执行指定方法
"execution(* com.example.service.UserService.*(..))"

# 执行参数匹配的方法
"execution(* com.example.service.*.*(String, ..))"
```

### @Aspect

切面注解。

```python
from harmony.aop.aspect import aspect

@aspect("logging")
class LoggingAspect:
    @before("execution(* com.example.service.*.*(..))")
    def log_before(self, join_point: JoinPoint):
        print(f"开始执行: {join_point.method_name}")

    @after("execution(* com.example.service.*.*(..))")
    def log_after(self, join_point: JoinPoint, result, exception):
        print(f"执行完成: {join_point.method_name}")
```

### 通知注解

```python
from harmony.aop.aop import before, after, around, after_returning, after_throwing

class MyAspect:
    @before("execution(* com.example.service.*.*(..))")
    def before_advice(self, join_point: JoinPoint):
        # 前置通知
        pass

    @after("execution(* com.example.service.*.*(..))")
    def after_advice(self, join_point: JoinPoint, result, exception):
        # 后置通知
        pass

    @around("execution(* com.example.service.*.*(..))")
    def around_advice(self, invocation: MethodInvocation):
        # 环绕通知
        pass

    @after_returning("execution(* com.example.service.*.*(..))")
    def after_returning_advice(self, join_point: JoinPoint, result):
        # 返回后通知
        pass

    @after_throwing("execution(* com.example.service.*.*(..))")
    def after_throwing_advice(self, join_point: JoinPoint, exception):
        # 异常后通知
        pass
```

## 扩展API

### PerformanceMonitor

性能监控器。

```python
from harmony.extensions.performance_monitor import PerformanceMonitor

# 创建性能监控器
monitor = PerformanceMonitor(collection_interval=5.0)

# 启用监控
monitor.enable()

# 注册指标
counter = monitor.registry.register_counter("requests", "请求总数")
gauge = monitor.registry.register_gauge("memory", "内存使用量")
timer = monitor.registry.register_timer("response_time", "响应时间")

# 使用指标
counter.increment()
gauge.set_value(1024)

# 获取报告
report = monitor.get_comprehensive_report()
```

### CacheManager

缓存管理器。

```python
from harmony.extensions.cache import CacheManager, CacheConfig, EvictionPolicy

# 创建缓存管理器
cache_manager = CacheManager()

# 配置缓存
cache_manager.configure_cache(
    name="user_cache",
    config=CacheConfig(
        max_size=1000,
        ttl=3600,
        eviction_policy=EvictionPolicy.LRU,
        enable_statistics=True
    )
)

# 获取缓存
cache = cache_manager.get_cache("user_cache")

# 使用缓存
cache.put("user:1", {"id": 1, "name": "张三"})
user = cache.get("user:1")

# 获取统计信息
stats = cache.get_statistics()
```

### ObjectPool

对象池。

```python
from harmony.extensions.object_pool import ObjectPool, PoolConfig

# 配置对象池
pool_config = PoolConfig(
    initial_size=5,
    max_size=50,
    max_idle_time=300,
    validation_interval=60
)

# 创建对象池
connection_pool = ObjectPool(
    factory=lambda: DatabaseConnection(),
    reset_func=lambda conn: conn.reset(),
    validate_func=lambda conn: conn.is_valid(),
    config=pool_config
)

# 使用对象池
with connection_pool.get_object() as conn:
    result = conn.execute_query("SELECT * FROM users")
```

### LifecycleManager

生命周期管理器。

```python
from harmony.extensions.lifecycle_events import LifecycleManager, LifecycleEvent

# 创建生命周期管理器
lifecycle_manager = LifecycleManager()

# 注册事件处理器
@lifecycle_manager.on_startup
def on_startup():
    print("应用启动")

@lifecycle_manager.on_shutdown
def on_shutdown():
    print("应用关闭")

# 发布事件
lifecycle_manager.publish_event(LifecycleEvent.STARTUP)
```

### HotReloadManager

热重载管理器。

```python
from harmony.extensions.hot_reload import HotReloadManager

# 创建热重载管理器
hot_reload = HotReloadManager()

# 启用热重载
hot_reload.enable(watch_dirs=["src/"], file_patterns=["*.py"])

# 监听文件变化
@hot_reload.on_file_changed
def on_file_changed(file_path: str, change_type: str):
    print(f"文件 {change_type}: {file_path}")
```

## 工具API

### StringUtil

字符串工具类。

```python
from harmony.util.string_util import StringUtil

# 检查邮箱格式
is_email = StringUtil.is_valid_email("user@example.com")

# 生成随机字符串
random_str = StringUtil.generate_random_string(16)

# 格式化字符串
formatted = StringUtil.format_template("Hello, {name}!", {"name": "World"})
```

### ValidationUtil

验证工具类。

```python
from harmony.util.validation_util import ValidationUtil

# 验证用户名
ValidationUtil.validate_username("testuser")

# 验证密码
ValidationUtil.validate_password("password123")

# 验证手机号
ValidationUtil.validate_phone("13812345678")
```

### DateUtil

日期工具类。

```python
from harmony.util.date_util import DateUtil

# 格式化日期
formatted_date = DateUtil.format_date(datetime.now(), "YYYY-MM-DD")

# 解析日期
parsed_date = DateUtil.parse_date("2023-12-25")

# 计算日期差
days_diff = DateUtil.date_diff(date1, date2)
```

### ReflectionUtil

反射工具类。

```python
from harmony.util.reflection_util import ReflectionUtil

# 获取类的方法
methods = ReflectionUtil.get_methods(MyClass)

# 获取类的属性
attributes = ReflectionUtil.get_attributes(MyClass)

# 调用方法
result = ReflectionUtil.invoke_method(instance, "method_name", args)

# 获取属性值
value = ReflectionUtil.get_attribute(instance, "attribute_name")
```

## 异常API

### Harmony 异常层次结构

```python
# 基础异常
class HarmonyException(Exception):
    """Harmony框架基础异常"""

# Bean相关异常
class BeanException(HarmonyException):
    """Bean异常基类"""

class NoSuchBeanDefinitionException(BeanException):
    """Bean定义不存在异常"""

class BeanCreationException(BeanException):
    """Bean创建异常"""

class BeanNotOfRequiredTypeException(BeanException):
    """Bean类型不匹配异常"""

# 依赖注入异常
class DependencyInjectionException(HarmonyException):
    """依赖注入异常"""

class CircularDependencyException(DependencyInjectionException):
    """循环依赖异常"""

# 配置异常
class ConfigurationException(HarmonyException):
    """配置异常"""

# AOP异常
class AopException(HarmonyException):
    """AOP异常"""
```

### 异常处理

```python
from harmony.exceptions.harmony_exceptions import (
    NoSuchBeanDefinitionException,
    BeanCreationException,
    CircularDependencyException
)

try:
    bean = context.get_bean("nonExistentBean")
except NoSuchBeanDefinitionException as e:
    print(f"Bean不存在: {e}")
except BeanCreationException as e:
    print(f"Bean创建失败: {e}")
except CircularDependencyException as e:
    print(f"循环依赖: {e}")
```

### 全局异常处理器

```python
from harmony.util.exception_util import GlobalExceptionHandler

# 创建全局异常处理器
handler = GlobalExceptionHandler()

# 注册异常处理器
@handler.handle(NoSuchBeanDefinitionException)
def handle_no_such_bean(e):
    return {"error": "Bean不存在", "details": str(e)}

@handler.handle(Exception)
def handle_general_exception(e):
    return {"error": "系统错误", "details": "请稍后重试"}
```

## 使用建议

1. **优先使用注解配置** - 注解配置更加简洁和易读
2. **合理选择作用域** - 无状态服务使用单例，有状态对象使用原型
3. **善用AOP** - 将日志、事务、缓存等横切关注点模块化
4. **充分利用扩展功能** - 性能监控、缓存、对象池等扩展能显著提升应用性能
5. **完善异常处理** - 使用框架提供的异常层次结构进行统一异常处理

这份完整的API参考文档涵盖了Harmony Framework的所有核心功能和扩展功能，为开发者提供了详细的API使用指南。