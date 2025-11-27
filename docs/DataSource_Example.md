# Harmony Framework 数据源管理模块使用示例

本文档展示了如何使用 Harmony Framework 的数据源管理模块进行数据库操作。

## 安装依赖

首先安装必要的依赖：

```bash
pip install sqlalchemy pymysql psycopg2-binary
```

## 基本配置

### 1. 数据源配置

```python
from harmony.extensions.data_source import (
    DataSourceConfig,
    DatabaseType,
    mysql_config,
    postgresql_config,
    sqlite_config
)

# 方式1: 直接创建配置
config = DataSourceConfig(
    name="default",
    database_type=DatabaseType.MYSQL,
    host="localhost",
    port=3306,
    database="myapp",
    username="root",
    password="password"
)

# 方式2: 使用便捷函数
mysql_config = mysql_config(
    host="localhost",
    database="myapp",
    username="root",
    password="password"
)

# 方式3: 使用构建器
config = DataSourceBuilder().database_type(DatabaseType.POSTGRESQL)\
    .host("localhost").port(5432).database("myapp")\
    .username("postgres").password("password")\
    .pool_config(ConnectionPoolConfig(pool_size=20, max_overflow=40))\
    .build()
```

### 2. 数据源管理器使用

```python
from harmony.extensions.data_source import DataSourceManager
from harmony.core.application_context import ApplicationContext

# 创建应用上下文
context = ApplicationContext()

# 创建数据源管理器
data_source_manager = DataSourceManager()

# 注册数据源
data_source_manager.register_data_source(config)

# 注册为Bean
context.register_bean_instance(DataSourceManager, data_source_manager, "dataSourceManager")

# 测试连接
if data_source_manager.test_connection():
    print("数据库连接成功!")
```

## 数据模型定义

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 基础模型类
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    author_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}')>"
```

## Repository 模式

### 1. 基础Repository实现

```python
from harmony.extensions.data_source import BaseRepository
from typing import List, Optional
from models import User, Article

class UserRepository(BaseRepository[User, int]):
    """用户Repository"""

    def get_entity_class(self):
        return User

    def find_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        return self.find_by(username=username)

    def find_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查找用户"""
        return self.find_by(email=email)

    def find_active_users(self) -> List[User]:
        """查找活跃用户"""
        return self.find_all_by(is_active=True)

    def find_users_created_after(self, date: datetime) -> List[User]:
        """查找指定日期之后创建的用户"""
        from sqlalchemy import and_
        return self.find_with_conditions(
            and_(User.created_at >= date, User.is_active == True)
        )

class ArticleRepository(BaseRepository[Article, int]):
    """文章Repository"""

    def get_entity_class(self):
        return Article

    def find_by_author(self, author_id: int) -> List[Article]:
        """根据作者查找文章"""
        return self.find_all_by(author_id=author_id)

    def find_published_articles(self) -> List[Article]:
        """查找已发布的文章"""
        return self.find_all_by(is_published=True)

    def find_articles_by_title(self, title_pattern: str) -> List[Article]:
        """根据标题模式查找文章"""
        from sqlalchemy import like
        return self.find_with_conditions(
            like(Article.title, f"%{title_pattern}%")
        )

    def find_articles_with_pagination(self, page: int = 0, size: int = 10) -> List[Article]:
        """分页查找文章"""
        return self.find_all_with_pagination(page, size)

    def count_articles_by_author(self, author_id: int) -> int:
        """统计作者的文章数量"""
        return self.count_by(author_id=author_id)
```

### 2. 简单Repository使用

```python
from harmony.extensions.data_source import SimpleRepository, create_repository

# 方式1: 直接使用简单Repository
user_repo = SimpleRepository(
    entity_class=User,
    data_source_manager=data_source_manager,
    data_source="default"
)

# 方式2: 使用工厂函数
article_repo = create_repository(
    entity_class=Article,
    data_source_manager=data_source_manager
)
```

## 事务管理

### 1. 声明式事务

```python
from harmony.extensions.data_source import (
    transactional,
    TransactionalClass,
    read_only,
    requires_new,
    rollback_for
)
from harmony.annotations.component import service

class UserService:
    """用户服务"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    @transactional
    def create_user(self, username: str, email: str, password: str) -> User:
        """创建用户（事务方法）"""
        user = User(
            username=username,
            email=email,
            password_hash=self._hash_password(password)
        )
        return self.user_repository.save(user)

    @read_only
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户（只读事务）"""
        return self.user_repository.find_by_id(user_id)

    @transactional(propagation="REQUIRES_NEW")
    def create_user_with_new_transaction(self, username: str, email: str, password: str) -> User:
        """在新事务中创建用户"""
        # 这个方法会在新的事务中执行
        user = User(
            username=username,
            email=email,
            password_hash=self._hash_password(password)
        )
        return self.user_repository.save(user)

    @transactional(rollback_for=[ValueError])
    def update_user_with_validation(self, user_id: int, **kwargs) -> Optional[User]:
        """带验证的更新用户"""
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # 验证逻辑
        if 'email' in kwargs and not self._is_valid_email(kwargs['email']):
            raise ValueError("Invalid email format")

        # 更新用户
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        return self.user_repository.update(user)

    def _hash_password(self, password: str) -> str:
        """密码哈希（示例）"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    def _is_valid_email(self, email: str) -> bool:
        """邮箱验证（示例）"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


@service
@TransactionalClass(read_only=False)
class BlogService:
    """博客服务（类级别事务）"""

    def __init__(self, user_repository: UserRepository, article_repository: ArticleRepository):
        self.user_repository = user_repository
        self.article_repository = article_repository

    def publish_article(self, article_id: int) -> Article:
        """发布文章（继承类级别事务设置）"""
        article = self.article_repository.find_by_id(article_id)
        if not article:
            raise ValueError("Article not found")

        article.is_published = True
        return self.article_repository.update(article)
```

### 2. 编程式事务

```python
from harmony.extensions.data_source import TransactionTemplate, TransactionDefinition

class OrderService:
    """订单服务（编程式事务）"""

    def __init__(self, transaction_template: TransactionTemplate):
        self.transaction_template = transaction_template

    def create_order_with_items(self, order_data: dict, items_data: list) -> dict:
        """创建订单及订单项（编程式事务）"""

        def create_order():
            # 在事务中执行的逻辑
            order = self._create_order(order_data)
            items = []
            for item_data in items_data:
                item = self._create_order_item(order.id, item_data)
                items.append(item)

            return {"order": order, "items": items}

        # 执行事务
        return self.transaction_template.execute(create_order)

    def batch_update_stock(self, updates: list) -> list:
        """批量更新库存（无返回值事务）"""

        def update_stock():
            for product_id, quantity_change in updates:
                self._update_product_stock(product_id, quantity_change)

        # 执行无返回值的事务
        self.transaction_template.execute_without_result(update_stock)

    def risky_operation(self, data: dict) -> dict:
        """风险操作（指定回滚异常）"""

        def operation():
            result = self._perform_operation(data)
            if not self._validate_result(result):
                raise ValueError("Operation validation failed")
            return result

        # 只在BusinessException时回滚
        return self.transaction_template.execute_with_rollback(
            operation, rollback_for=[BusinessException]
        )
```

## 完整应用示例

### 1. 配置类

```python
from harmony.annotations.component import configuration
from harmony.annotations.bean import bean
from harmony.extensions.data_source import (
    DataSourceConfig,
    DatabaseType,
    DataSourceManager,
    ConnectionPoolConfig
)

@configuration
class DatabaseConfig:

    @bean
    def data_source_config(self) -> DataSourceConfig:
        """数据源配置"""
        return DataSourceConfig(
            name="default",
            database_type=DatabaseType.MYSQL,
            host="${database.host:localhost}",
            port="${database.port:3306}",
            database="${database.name:myapp}",
            username="${database.username:root}",
            password="${database.password:}",
            pool_config=ConnectionPoolConfig(
                pool_size=20,
                max_overflow=40,
                pool_timeout=30,
                pool_recycle=3600
            )
        )

    @bean
    def data_source_manager(self, config: DataSourceConfig) -> DataSourceManager:
        """数据源管理器"""
        manager = DataSourceManager()
        manager.register_data_source(config)
        return manager

    @bean
    def user_repository(self, data_source_manager: DataSourceManager) -> UserRepository:
        """用户Repository"""
        return UserRepository(data_source_manager=data_source_manager)

    @bean
    def article_repository(self, data_source_manager: DataSourceManager) -> ArticleRepository:
        """文章Repository"""
        return ArticleRepository(data_source_manager=data_source_manager)
```

### 2. 服务层

```python
from harmony.annotations.component import service
from harmony.annotations.component import constructor_autowired
from harmony.extensions.data_source import transactional

@service
class BlogApplicationService:

    @constructor_autowired
    def __init__(self,
                 user_service: UserService,
                 article_service: ArticleService,
                 user_repository: UserRepository,
                 article_repository: ArticleRepository):
        self.user_service = user_service
        self.article_service = article_service
        self.user_repository = user_repository
        self.article_repository = article_repository

    @transactional
    def create_user_with_first_article(self,
                                     user_data: dict,
                                     article_data: dict) -> dict:
        """创建用户并发表第一篇文章（事务操作）"""

        # 创建用户
        user = self.user_service.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password']
        )

        # 创建文章
        article = Article(
            title=article_data['title'],
            content=article_data['content'],
            author_id=user.id,
            is_published=True
        )
        article = self.article_repository.save(article)

        return {
            "user": user,
            "article": article
        }

    def get_user_articles(self, user_id: int, page: int = 0, size: int = 10) -> dict:
        """获取用户文章列表"""
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        articles = self.article_repository.find_articles_with_pagination(page, size)
        total_count = self.article_repository.count_by(author_id=user_id)

        return {
            "user": user,
            "articles": articles,
            "total_count": total_count,
            "page": page,
            "size": size
        }
```

### 3. 启动类

```python
from harmony.core.application_context import ApplicationContext
from harmony.extensions.data_source import DataSourceManager
from config import DatabaseConfig
from models import Base

def main():
    # 创建应用上下文
    context = ApplicationContext()

    # 注册配置类
    context.register_bean(DatabaseConfig, "databaseConfig")

    # 组件扫描
    context.component_scan("com.example.services", "com.example.repositories")

    # 刷新上下文
    context.refresh()

    try:
        # 获取数据源管理器
        data_source_manager = context.get_bean("dataSourceManager")

        # 创建表结构
        print("Creating database tables...")
        data_source_manager.create_all_tables(base_class=Base)
        print("Tables created successfully!")

        # 获取服务
        blog_service = context.get_bean("blogApplicationService")

        # 示例使用
        result = blog_service.create_user_with_first_article(
            user_data={
                "username": "john_doe",
                "email": "john@example.com",
                "password": "secure_password"
            },
            article_data={
                "title": "My First Article",
                "content": "This is the content of my first article."
            }
        )

        print(f"Created user: {result['user'].username}")
        print(f"Created article: {result['article'].title}")

        # 获取用户文章
        user_articles = blog_service.get_user_articles(result['user'].id)
        print(f"User has {user_articles['total_count']} articles")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭应用上下文
        context.close()

if __name__ == "__main__":
    main()
```

## 高级功能

### 1. 多数据源配置

```python
@configuration
class MultiDataSourceConfig:

    @bean("primaryDataSource")
    def primary_data_source_config(self) -> DataSourceConfig:
        """主数据源配置"""
        return mysql_config(
            host="localhost",
            database="primary_db",
            username="user",
            password="password"
        )

    @bean("secondaryDataSource")
    def secondary_data_source_config(self) -> DataSourceConfig:
        """从数据源配置"""
        return postgresql_config(
            host="localhost",
            database="secondary_db",
            username="postgres",
            password="password"
        )

    @bean
    def data_source_manager(self,
                           primary_config: DataSourceConfig,
                           secondary_config: DataSourceConfig) -> DataSourceManager:
        """多数据源管理器"""
        manager = DataSourceManager()
        manager.register_data_source(primary_config)
        manager.register_data_source(secondary_config)
        return manager

    @bean
    def primary_user_repository(self, data_source_manager: DataSourceManager) -> UserRepository:
        """主库用户Repository"""
        return UserRepository(
            data_source_manager=data_source_manager,
            data_source="primaryDataSource"
        )

    @bean
    def secondary_user_repository(self, data_source_manager: DataSourceManager) -> UserRepository:
        """从库用户Repository"""
        return UserRepository(
            data_source_manager=data_source_manager,
            data_source="secondaryDataSource"
        )
```

### 2. 读写分离

```python
@service
class ReadWriteSeparatedUserService:

    def __init__(self,
                 write_repository: UserRepository,
                 read_repository: UserRepository):
        self.write_repository = write_repository  # 写库
        self.read_repository = read_repository     # 读库

    @transactional(data_source="primaryDataSource")
    def create_user(self, username: str, email: str, password: str) -> User:
        """写入操作使用主库"""
        return self.write_repository.save(User(
            username=username,
            email=email,
            password_hash=self._hash_password(password)
        ))

    @read_only
    def get_user(self, user_id: int) -> Optional[User]:
        """读取操作使用从库"""
        return self.read_repository.find_by_id(user_id)
```

### 3. 健康检查和监控

```python
@service
class DatabaseHealthService:

    def __init__(self, data_source_manager: DataSourceManager):
        self.data_source_manager = data_source_manager

    def health_check(self) -> dict:
        """数据库健康检查"""
        return {
            "status": "UP" if self._is_healthy() else "DOWN",
            "details": self.data_source_manager.health_check()
        }

    def get_connection_info(self) -> dict:
        """获取连接信息"""
        info = {}
        for name in self.data_source_manager.list_data_sources():
            info[name] = self.data_source_manager.get_connection_info(name)
        return info

    def _is_healthy(self) -> bool:
        """检查数据库是否健康"""
        try:
            results = self.data_source_manager.health_check()
            return all(result["connected"] for result in results.values())
        except:
            return False
```

## 最佳实践

1. **配置管理**: 使用配置文件管理数据库连接信息
2. **连接池**: 合理配置连接池大小，避免连接泄漏
3. **事务边界**: 明确定义事务边界，避免长事务
4. **异常处理**: 正确处理数据库异常和事务回滚
5. **性能优化**: 使用索引、批量操作、分页查询等优化性能
6. **读写分离**: 对于高并发应用，考虑使用读写分离
7. **健康检查**: 定期检查数据库连接状态
8. **资源清理**: 确保会话和连接正确关闭

这个数据源管理模块为 Harmony Framework 提供了完整的数据库访问能力，支持多种数据库、事务管理、连接池和Repository模式，是企业级应用开发的理想选择。