# Harmony Framework 快速入门指南

## 🚀 5分钟快速体验

### 1. 基础示例

```python
from harmony.core.application_context import ApplicationContext

# 创建应用上下文
context = ApplicationContext()


# 定义服务类
class UserService:
    def create_user(self, name):
        return f"用户 {name} 创建成功"


# 注册并使用
context.register_bean(UserService, "userService")
service = context.get_bean("userService")

print(service.create_user("张三"))  # 输出: 用户 张三 创建成功
context.close()
```

### 2. 依赖注入

```python
class DatabaseService:
    def get_connection(self):
        return "数据库连接已建立"


class UserService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def save_user(self, name):
        return f"保存用户 {name} 到 {self.db_service.get_connection()}"


# 注册Bean
context.register_bean(DatabaseService, "databaseService")
context.register_bean(UserService, "userService")

# 自动依赖注入
user_service = context.get_bean("userService")
print(user_service.save_user("李四"))
```

### 3. 作用域管理

```python
from harmony.core.scope import ScopeType


# 单例模式（默认）
@component(scope=ScopeType.SINGLETON.value)
class ConfigService:
    def get_config(self):
        return "全局配置"


# 原型模式
@component(scope=ScopeType.PROTOTYPE.value)
class UserSession:
    def __init__(self):
        self.session_id = id(self)  # 每次获取都不同


# 注册
context.register_bean(ConfigService, "configService")
context.register_bean(UserSession, "userSession")

# 测试作用域
config1 = context.get_bean("configService")
config2 = context.get_bean("configService")
print(f"配置服务是否相同: {config1 is config2}")  # True

session1 = context.get_bean("userSession")
session2 = context.get_bean("userSession")
print(f"会话服务是否相同: {session1 is session2}")  # False
```

### 4. 注解驱动开发

```python
from harmony.annotations.component import component, service, repository


# 使用注解定义组件
@service("userService")
class UserService:
    def __init__(self):
        self.name = "用户服务"


@repository("userRepository")
class UserRepository:
    def find_all(self):
        return ["用户1", "用户2", "用户3"]


@component("appController")
class AppController:
    def __init__(self, user_service: UserService, user_repository: UserRepository):
        self.user_service = user_service
        self.user_repository = user_repository

    def run(self):
        users = self.user_repository.find_all()
        return f"{self.user_service.name} 管理着: {', '.join(users)}"


# 组件扫描
context.component_scan("com.example")
context.refresh()

controller = context.get_bean("appController")
print(controller.run())
```

### 5. 配置管理

```python
# 添加配置
context.add_property_source({
    "database.url": "jdbc:mysql://localhost:3306/test",
    "app.name": "Harmony Demo",
    "app.debug": "true"
})


# 使用配置的Bean
class AppConfig:
    def __init__(self):
        self.db_url = context.get_property("database.url")
        self.app_name = context.get_property("app.name")
        self.debug = context.get_property("app.debug", type=bool)


context.register_bean(AppConfig, "appConfig")
config = context.get_bean("appConfig")

print(f"应用名: {config.app_name}")
print(f"数据库: {config.db_url}")
print(f"调试模式: {config.debug}")
```

## 🏗️ 项目结构建议

```
your-project/
├── src/
│   ├── your_app/
│   │   ├── __init__.py
│   │   ├── controller/          # 控制层
│   │   │   ├── __init__.py
│   │   │   └── user_controller.py
│   │   ├── service/             # 服务层
│   │   │   ├── __init__.py
│   │   │   └── user_service.py
│   │   ├── repository/          # 数据访问层
│   │   │   ├── __init__.py
│   │   │   └── user_repository.py
│   │   ├── config/              # 配置
│   │   │   ├── __init__.py
│   │   │   └── app_config.py
│   │   └── model/               # 数据模型
│   │       ├── __init__.py
│   │       └── user.py
│   └── main.py                  # 应用入口
├── tests/                       # 测试
├── config/                      # 配置文件
└── requirements.txt
```

## 📋 常用注解速查

| 注解               | 作用        | 示例                                    |
|------------------|-----------|---------------------------------------|
| `@service`       | 标记服务层组件   | `@service("userService")`             |
| `@repository`    | 标记数据访问层组件 | `@repository("userRepository")`       |
| `@controller`    | 标记控制层组件   | `@controller("userController")`       |
| `@component`     | 通用组件标记    | `@component("utilService")`           |
| `@configuration` | 配置类       | `@configuration class DatabaseConfig` |
| `@bean`          | 手动定义Bean  | `@bean def data_source()`             |

## ⚡ 性能技巧

1. **使用单例模式**：无状态服务使用单例作用域
2. **延迟初始化**：大型对象使用 `lazy=True`
3. **批量操作**：注册多个Bean时使用批量方法
4. **连接池**：数据库和缓存使用连接池
5. **缓存策略**：频繁访问的数据使用缓存

## 🐛 常见问题解决

### 问题1: Bean找不到

```python
# 确保Bean已注册
context.register_bean(MyService, "myService")
# 或使用组件扫描
context.component_scan("com.example.service")
context.refresh()
```

### 问题2: 循环依赖

```python
# 使用setter注入或@Lazy注解
class ServiceA:
    def set_service_b(self, service_b):
        self.service_b = service_b
```

### 问题3: 作用域错误

```python
# 确保选择了正确的作用域
context.register_bean(MyBean, "myBean", scope=ScopeType.PROTOTYPE.value)
```

## 🔗 更多资源

- 📖 [完整用户手册](./Harmony_Framework_User_Manual.md)
- 🐛 [问题反馈](https://github.com/your-org/harmony-framework/issues)
- 💬 [社区讨论](https://github.com/your-org/harmony-framework/discussions)
- 📚 [API文档](https://harmony-framework.readthedocs.io)

## 🎉 开始你的Harmony之旅！

现在你已经了解了Harmony Framework的基础知识，可以开始构建你的应用了！

**记住**: Harmony Framework 的核心理念是简单、高效、可扩展。

如果需要更多帮助，请参考完整的用户手册或联系我们的技术支持团队。

---

*Happy Coding with Harmony Framework! 🌟*