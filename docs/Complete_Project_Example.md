# Harmony Framework 完整项目示例

## 🎯 项目概述

本文档通过一个完整的电商管理系统示例，展示如何使用 Harmony Framework 构建实际的企业级应用。该示例涵盖了从项目结构设计到部署的完整开发流程。

## 📁 项目结构

```
ecommerce-system/
├── src/
│   ├── __init__.py
│   ├── main.py                          # 应用入口
│   ├── config/                          # 配置模块
│   │   ├── __init__.py
│   │   ├── app_config.py               # 应用配置
│   │   ├── database_config.py          # 数据库配置
│   │   └── redis_config.py             # Redis配置
│   ├── model/                          # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py                     # 用户模型
│   │   ├── product.py                  # 产品模型
│   │   ├── order.py                    # 订单模型
│   │   └── cart.py                     # 购物车模型
│   ├── repository/                     # 数据访问层
│   │   ├── __init__.py
│   │   ├── user_repository.py          # 用户数据访问
│   │   ├── product_repository.py       # 产品数据访问
│   │   ├── order_repository.py         # 订单数据访问
│   │   └── base_repository.py          # 基础数据访问
│   ├── service/                        # 服务层
│   │   ├── __init__.py
│   │   ├── user_service.py             # 用户服务
│   │   ├── product_service.py          # 产品服务
│   │   ├── order_service.py            # 订单服务
│   │   ├── cart_service.py             # 购物车服务
│   │   ├── payment_service.py          # 支付服务
│   │   └── email_service.py            # 邮件服务
│   ├── controller/                     # 控制层
│   │   ├── __init__.py
│   │   ├── user_controller.py          # 用户控制器
│   │   ├── product_controller.py       # 产品控制器
│   │   ├── order_controller.py         # 订单控制器
│   │   └── cart_controller.py          # 购物车控制器
│   ├── security/                       # 安全模块
│   │   ├── __init__.py
│   │   ├── auth_service.py             # 认证服务
│   │   ├── permission_service.py       # 权限服务
│   │   └── jwt_util.py                 # JWT工具
│   ├── aspect/                         # 切面模块
│   │   ├── __init__.py
│   │   ├── logging_aspect.py           # 日志切面
│   │   ├── transaction_aspect.py       # 事务切面
│   │   ├── cache_aspect.py             # 缓存切面
│   │   └── security_aspect.py          # 安全切面
│   └── util/                           # 工具模块
│       ├── __init__.py
│       ├── date_util.py                # 日期工具
│       ├── string_util.py              # 字符串工具
│       └── validation_util.py          # 验证工具
├── config/                             # 配置文件
│   ├── application.properties          # 应用配置
│   ├── application-dev.properties      # 开发环境配置
│   ├── application-prod.properties     # 生产环境配置
│   └── logback.xml                     # 日志配置
├── tests/                              # 测试模块
│   ├── __init__.py
│   ├── unit/                           # 单元测试
│   │   ├── test_user_service.py
│   │   ├── test_product_service.py
│   │   └── test_order_service.py
│   ├── integration/                    # 集成测试
│   │   ├── test_user_integration.py
│   │   └── test_order_integration.py
│   └── performance/                    # 性能测试
│       └── test_performance.py
├── docs/                               # 文档
│   ├── api/                            # API文档
│   ├── deployment/                     # 部署文档
│   └── user_guide/                     # 用户指南
├── scripts/                            # 脚本
│   ├── init_db.py                      # 数据库初始化
│   ├── migrate.py                      # 数据迁移
│   └── deploy.sh                       # 部署脚本
├── requirements.txt                    # 依赖文件
├── README.md                           # 项目说明
├── Dockerfile                          # Docker文件
└── docker-compose.yml                  # Docker编排文件
```

## 🚀 应用入口

### main.py - 应用启动类

```python
import sys
import os
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from harmony.core.application_context import ApplicationContext
from harmony.config.environment import Environment
from harmony.extensions.performance_monitor import PerformanceMonitor
from harmony.extensions.lifecycle_events import LifecycleManager
from harmony.aop.aop import AspectManager

from config.app_config import AppConfig
from aspect.logging_aspect import LoggingAspect
from aspect.transaction_aspect import TransactionAspect
from aspect.cache_aspect import CacheAspect
from aspect.security_aspect import SecurityAspect

class EcommerceApplication:
    """电商应用主类"""

    def __init__(self):
        self.context = ApplicationContext()
        self.environment = Environment()
        self.performance_monitor = PerformanceMonitor()
        self.lifecycle_manager = LifecycleManager()
        self.aspect_manager = AspectManager()

    def bootstrap(self):
        """启动应用"""
        print("🚀 启动电商系统...")

        # 1. 设置环境
        self._setup_environment()

        # 2. 加载配置
        self._load_configurations()

        # 3. 注册切面
        self._register_aspects()

        # 4. 组件扫描
        self._scan_components()

        # 5. 刷新上下文
        self._refresh_context()

        # 6. 启动监控
        self._start_monitoring()

        print("✅ 电商系统启动完成!")

    def _setup_environment(self):
        """设置运行环境"""
        profile = os.getenv("SPRING_PROFILES_ACTIVE", "development")
        self.environment.set_active_profiles(profile)
        print(f"📋 当前环境: {profile}")

    def _load_configurations(self):
        """加载配置文件"""
        # 加载应用配置
        self.context.register_configuration(AppConfig)

        # 加载属性文件
        config_file = f"config/application-{self.environment.get_active_profile()}.properties"
        if os.path.exists(config_file):
            self.context.load_properties_from_file(config_file)
            print(f"📄 加载配置文件: {config_file}")

    def _register_aspects(self):
        """注册切面"""
        # 日志切面
        logging_aspect = LoggingAspect(self.aspect_manager)

        # 事务切面
        transaction_aspect = TransactionAspect(self.aspect_manager)

        # 缓存切面
        cache_aspect = CacheAspect(self.aspect_manager)

        # 安全切面
        security_aspect = SecurityAspect(self.aspect_manager)

        print("🔧 切面注册完成")

    def _scan_components(self):
        """组件扫描"""
        base_packages = [
            "config",
            "model",
            "repository",
            "service",
            "controller",
            "security",
            "util"
        ]

        for package in base_packages:
            try:
                self.context.component_scan(package)
                print(f"📦 扫描包: {package}")
            except Exception as e:
                print(f"⚠️  包扫描失败 {package}: {e}")

    def _refresh_context(self):
        """刷新应用上下文"""
        self.context.refresh()
        print("🔄 应用上下文刷新完成")

    def _start_monitoring(self):
        """启动监控"""
        # 启用性能监控
        self.performance_monitor.enable()

        # 发布启动事件
        self.lifecycle_manager.publish_event("STARTUP")

        print("📊 监控系统已启动")

    def shutdown(self):
        """关闭应用"""
        print("🛑 关闭电商系统...")

        # 发布关闭事件
        self.lifecycle_manager.publish_event("SHUTDOWN")

        # 关闭性能监控
        self.performance_monitor.disable()

        # 关闭应用上下文
        self.context.close()

        print("✅ 电商系统已关闭")

def main():
    """主函数"""
    app = EcommerceApplication()

    try:
        app.bootstrap()

        # 保持应用运行
        print("🌟 电商系统运行中... (按 Ctrl+C 停止)")

        # 注册信号处理器
        import signal
        def signal_handler(signum, frame):
            print("\n📡 接收到停止信号")
            app.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 主循环
        while True:
            import time
            time.sleep(1)

    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        app.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## ⚙️ 配置模块

### config/app_config.py - 应用配置

```python
from harmony.annotations.component import configuration, bean
from harmony.config.configuration import ConfigurationProperties
from harmony.config.environment import Environment
from harmony.extensions.cache import CacheManager, CacheConfig, EvictionPolicy

@configuration
class AppConfig:
    """应用配置类"""

    def __init__(self):
        self.env = Environment()

    @bean
    def environment(self):
        """环境配置"""
        return self.env

    @bean
    def cache_manager(self):
        """缓存管理器"""
        cache_manager = CacheManager()

        # 用户缓存配置
        cache_manager.configure_cache(
            name="user_cache",
            config=CacheConfig(
                max_size=1000,
                ttl=3600,  # 1小时
                eviction_policy=EvictionPolicy.LRU,
                enable_statistics=True
            )
        )

        # 产品缓存配置
        cache_manager.configure_cache(
            name="product_cache",
            config=CacheConfig(
                max_size=5000,
                ttl=7200,  # 2小时
                eviction_policy=EvictionPolicy.LFU,
                enable_statistics=True
            )
        )

        # 订单缓存配置
        cache_manager.configure_cache(
            name="order_cache",
            config=CacheConfig(
                max_size=2000,
                ttl=1800,  # 30分钟
                eviction_policy=EvictionPolicy.LRU,
                enable_statistics=True
            )
        )

        return cache_manager

@ConfigurationProperties(prefix="app")
class ApplicationProperties:
    """应用属性配置"""

    def __init__(self):
        self.name = "电商管理系统"
        self.version = "1.0.0"
        self.description = "基于Harmony Framework的电商管理系统"
        self.debug = False

    def get_app_info(self):
        """获取应用信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "debug": self.debug,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "framework": "Harmony Framework"
        }
```

### config/database_config.py - 数据库配置

```python
import os
from harmony.annotations.component import configuration, bean
from harmony.config.configuration import ConfigurationProperties

@configuration
class DatabaseConfig:
    """数据库配置"""

    @bean
    def database_properties(self):
        """数据库属性"""
        return DatabaseProperties()

@ConfigurationProperties(prefix="database")
class DatabaseProperties:
    """数据库属性配置"""

    def __init__(self):
        self.url = os.getenv("DATABASE_URL", "sqlite:///ecommerce.db")
        self.username = os.getenv("DATABASE_USERNAME", "")
        self.password = os.getenv("DATABASE_PASSWORD", "")
        self.driver = os.getenv("DATABASE_DRIVER", "sqlite")
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.max_lifetime = int(os.getenv("DATABASE_MAX_LIFETIME", "3600"))
        self.validation_query = "SELECT 1"

    def get_connection_string(self):
        """获取连接字符串"""
        if self.driver == "mysql":
            return f"mysql+pymysql://{self.username}:{self.password}@localhost:3306/ecommerce"
        elif self.driver == "postgresql":
            return f"postgresql://{self.username}:{self.password}@localhost:5432/ecommerce"
        elif self.driver == "sqlite":
            return self.url
        else:
            raise ValueError(f"不支持的数据库驱动: {self.driver}")
```

## 🗃️ 数据模型

### model/user.py - 用户模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    CUSTOMER = "customer"
    MERCHANT = "merchant"

class UserStatus(Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"

@dataclass
class User:
    """用户实体类"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER
    status: UserStatus = UserStatus.ACTIVE
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None

    def get_full_name(self) -> str:
        """获取全名"""
        return f"{self.first_name} {self.last_name}".strip()

    def is_active(self) -> bool:
        """检查用户是否激活"""
        return self.status == UserStatus.ACTIVE

    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.role == UserRole.ADMIN

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }

@dataclass
class UserProfile:
    """用户档案"""
    user_id: int
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    preferences: dict = field(default_factory=dict)

    def get_full_address(self) -> str:
        """获取完整地址"""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.country:
            parts.append(self.country)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts)
```

### model/product.py - 产品模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class ProductStatus(Enum):
    """产品状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"

@dataclass
class Product:
    """产品实体类"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    sku: str = ""
    price: Decimal = Decimal('0.00')
    original_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    currency: str = "CNY"
    status: ProductStatus = ProductStatus.ACTIVE
    category_id: Optional[int] = None
    brand: Optional[str] = None
    images: List[str] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    inventory_count: int = 0
    min_stock_level: int = 0
    weight: Optional[Decimal] = None
    dimensions: Optional[dict] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    def is_available(self) -> bool:
        """检查产品是否可用"""
        return (self.status == ProductStatus.ACTIVE and
                self.inventory_count > 0)

    def get_discount_percentage(self) -> Decimal:
        """获取折扣百分比"""
        if not self.original_price or self.original_price <= self.price:
            return Decimal('0')

        discount = (self.original_price - self.price) / self.original_price * 100
        return discount.quantize(Decimal('0.01'))

    def is_low_stock(self) -> bool:
        """检查库存是否过低"""
        return self.inventory_count <= self.min_stock_level

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sku": self.sku,
            "price": float(self.price),
            "original_price": float(self.original_price) if self.original_price else None,
            "currency": self.currency,
            "status": self.status.value,
            "category_id": self.category_id,
            "brand": self.brand,
            "images": self.images,
            "attributes": self.attributes,
            "tags": self.tags,
            "inventory_count": self.inventory_count,
            "is_available": self.is_available(),
            "discount_percentage": float(self.get_discount_percentage()),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class ProductCategory:
    """产品分类"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    parent_id: Optional[int] = None
    level: int = 1
    sort_order: int = 0
    is_active: bool = True
    image_url: Optional[str] = None

    def get_full_path(self, categories: dict) -> str:
        """获取完整分类路径"""
        if not self.parent_id:
            return self.name

        parent = categories.get(self.parent_id)
        if parent:
            return f"{parent.get_full_path(categories)} > {self.name}"

        return self.name
```

### model/order.py - 订单模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(Enum):
    """支付状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

@dataclass
class OrderItem:
    """订单项"""
    id: Optional[int] = None
    order_id: Optional[int] = None
    product_id: int
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    product_snapshot: Dict[str, Any] = field(default_factory=dict)

    def get_total(self) -> Decimal:
        """获取小计"""
        return self.unit_price * self.quantity

@dataclass
class Order:
    """订单实体类"""
    id: Optional[int] = None
    order_number: str = ""
    user_id: int
    user_email: str = ""
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    currency: str = "CNY"
    subtotal: Decimal = Decimal('0.00')
    tax_amount: Decimal = Decimal('0.00')
    shipping_fee: Decimal = Decimal('0.00')
    discount_amount: Decimal = Decimal('0.00')
    total_amount: Decimal = Decimal('0.00')
    items: List[OrderItem] = field(default_factory=list)
    shipping_address: Dict[str, Any] = field(default_factory=dict)
    billing_address: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    def calculate_totals(self):
        """计算订单总额"""
        self.subtotal = sum(item.get_total() for item in self.items)
        self.total_amount = (
            self.subtotal +
            self.tax_amount +
            self.shipping_fee -
            self.discount_amount
        )

    def add_item(self, product_id: int, product_name: str, product_sku: str,
                 quantity: int, unit_price: Decimal, product_snapshot: Dict[str, Any] = None):
        """添加订单项"""
        item = OrderItem(
            product_id=product_id,
            product_name=product_name,
            product_sku=product_sku,
            quantity=quantity,
            unit_price=unit_price,
            total_price=unit_price * quantity,
            product_snapshot=product_snapshot or {}
        )
        self.items.append(item)
        self.calculate_totals()

    def can_cancel(self) -> bool:
        """检查订单是否可以取消"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]

    def is_paid(self) -> bool:
        """检查订单是否已支付"""
        return self.payment_status == PaymentStatus.PAID

    def get_status_display(self) -> str:
        """获取状态显示文本"""
        status_map = {
            OrderStatus.PENDING: "待处理",
            OrderStatus.CONFIRMED: "已确认",
            OrderStatus.PROCESSING: "处理中",
            OrderStatus.SHIPPED: "已发货",
            OrderStatus.DELIVERED: "已送达",
            OrderStatus.CANCELLED: "已取消",
            OrderStatus.REFUNDED: "已退款"
        }
        return status_map.get(self.status, self.status.value)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "status": self.status.value,
            "payment_status": self.payment_status.value,
            "status_display": self.get_status_display(),
            "currency": self.currency,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "shipping_fee": float(self.shipping_fee),
            "discount_amount": float(self.discount_amount),
            "total_amount": float(self.total_amount),
            "item_count": len(self.items),
            "items": [item.__dict__ for item in self.items],
            "shipping_address": self.shipping_address,
            "billing_address": self.billing_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None
        }
```

## 🏪 数据访问层

### repository/base_repository.py - 基础仓储

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar
from contextlib import contextmanager

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """基础仓储接口"""

    @abstractmethod
    def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    def find_by_id(self, entity_id: int) -> Optional[T]:
        """根据ID查找实体"""
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """查找所有实体"""
        pass

    @abstractmethod
    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """根据条件查找实体"""
        pass

    @abstractmethod
    def count(self, criteria: Dict[str, Any] = None) -> int:
        """统计实体数量"""
        pass

class DatabaseConnection:
    """数据库连接管理"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None

    @contextmanager
    def get_cursor(self):
        """获取数据库游标"""
        if not self._connection:
            self._connection = self._create_connection()

        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def _create_connection(self):
        """创建数据库连接"""
        # 这里应该实现真实的数据库连接逻辑
        # 为了示例，返回一个模拟对象
        class MockCursor:
            def execute(self, sql, params=None):
                print(f"执行SQL: {sql}, 参数: {params}")
                return self

            def fetchone(self):
                return None

            def fetchall(self):
                return []

            def close(self):
                pass

        class MockConnection:
            def cursor(self):
                return MockCursor()

            def commit(self):
                print("提交事务")

            def rollback(self):
                print("回滚事务")

            def close(self):
                print("关闭连接")

        return MockConnection()

class BaseRepositoryImpl(BaseRepository[T]):
    """基础仓储实现"""

    def __init__(self, connection: DatabaseConnection, table_name: str):
        self.connection = connection
        self.table_name = table_name
        self._entity_class = None

    def set_entity_class(self, entity_class: type):
        """设置实体类"""
        self._entity_class = entity_class

    def create(self, entity: T) -> T:
        """创建实体"""
        with self.connection.get_cursor() as cursor:
            # 构建插入SQL
            fields = []
            placeholders = []
            values = []

            for key, value in entity.__dict__.items():
                if key != 'id' and value is not None:
                    fields.append(key)
                    placeholders.append('?')
                    values.append(value)

            sql = f"""
            INSERT INTO {self.table_name} ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            """

            cursor.execute(sql, values)

            # 模拟获取插入的ID
            if hasattr(entity, 'id'):
                entity.id = 1  # 模拟自增ID

            self.connection._connection.commit()
            return entity

    def update(self, entity: T) -> T:
        """更新实体"""
        if not hasattr(entity, 'id') or entity.id is None:
            raise ValueError("实体ID不能为空")

        with self.connection.get_cursor() as cursor:
            # 构建更新SQL
            set_clauses = []
            values = []

            for key, value in entity.__dict__.items():
                if key != 'id' and value is not None:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

            if not set_clauses:
                return entity

            values.append(entity.id)

            sql = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = ?
            """

            cursor.execute(sql, values)
            self.connection._connection.commit()
            return entity

    def delete(self, entity_id: int) -> bool:
        """删除实体"""
        with self.connection.get_cursor() as cursor:
            sql = f"DELETE FROM {self.table_name} WHERE id = ?"
            cursor.execute(sql, [entity_id])
            self.connection._connection.commit()
            return cursor.rowcount > 0

    def find_by_id(self, entity_id: int) -> Optional[T]:
        """根据ID查找实体"""
        with self.connection.get_cursor() as cursor:
            sql = f"SELECT * FROM {self.table_name} WHERE id = ?"
            cursor.execute(sql, [entity_id])
            row = cursor.fetchone()

            if row and self._entity_class:
                return self._row_to_entity(row)

            return None

    def find_all(self) -> List[T]:
        """查找所有实体"""
        with self.connection.get_cursor() as cursor:
            sql = f"SELECT * FROM {self.table_name}"
            cursor.execute(sql)
            rows = cursor.fetchall()

            if self._entity_class:
                return [self._row_to_entity(row) for row in rows]

            return []

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """根据条件查找实体"""
        if not criteria:
            return self.find_all()

        with self.connection.get_cursor() as cursor:
            where_clauses = []
            values = []

            for key, value in criteria.items():
                where_clauses.append(f"{key} = ?")
                values.append(value)

            sql = f"""
            SELECT * FROM {self.table_name}
            WHERE {' AND '.join(where_clauses)}
            """

            cursor.execute(sql, values)
            rows = cursor.fetchall()

            if self._entity_class:
                return [self._row_to_entity(row) for row in rows]

            return []

    def count(self, criteria: Dict[str, Any] = None) -> int:
        """统计实体数量"""
        with self.connection.get_cursor() as cursor:
            if criteria:
                where_clauses = []
                values = []

                for key, value in criteria.items():
                    where_clauses.append(f"{key} = ?")
                    values.append(value)

                sql = f"""
                SELECT COUNT(*) FROM {self.table_name}
                WHERE {' AND '.join(where_clauses)}
                """
                cursor.execute(sql, values)
            else:
                sql = f"SELECT COUNT(*) FROM {self.table_name}"
                cursor.execute(sql)

            row = cursor.fetchone()
            return row[0] if row else 0

    def _row_to_entity(self, row) -> T:
        """将数据库行转换为实体对象"""
        if not self._entity_class:
            raise ValueError("实体类未设置")

        # 简化的转换逻辑，实际实现需要根据数据库返回的行格式进行调整
        entity_data = {}
        for i, value in enumerate(row):
            # 假设行的顺序与实体的属性顺序一致
            # 实际实现中应该使用列名映射
            if i < len(self._entity_class.__annotations__):
                attr_name = list(self._entity_class.__annotations__.keys())[i]
                entity_data[attr_name] = value

        return self._entity_class(**entity_data)
```

## 🛍️ 服务层

### service/user_service.py - 用户服务

```python
import hashlib
import secrets
from typing import Optional, List
from harmony.annotations.component import service, constructor_autowired
from harmony.annotations.lifecycle import PostConstruct, PreDestroy

from model.user import User, UserProfile, UserRole, UserStatus
from repository.user_repository import UserRepository
from util.string_util import StringUtil
from util.validation_util import ValidationUtil
from aspect.cache_aspect import cache

@service("userService")
class UserService:
    """用户服务"""

    @constructor_autowired
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.password_salt = secrets.token_hex(16)

    @PostConstruct
    def init(self):
        """初始化服务"""
        print("UserService 初始化完成")

    def create_user(self, username: str, email: str, password: str,
                   first_name: str, last_name: str, role: UserRole = UserRole.CUSTOMER) -> User:
        """创建用户"""
        # 验证输入
        ValidationUtil.validate_username(username)
        ValidationUtil.validate_email(email)
        ValidationUtil.validate_password(password)

        # 检查用户名和邮箱是否已存在
        if self.get_user_by_username(username):
            raise ValueError(f"用户名 {username} 已存在")

        if self.get_user_by_email(email):
            raise ValueError(f"邮箱 {email} 已被注册")

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            status=UserStatus.ACTIVE
        )

        return self.user_repository.create(user)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not user.is_active():
            raise ValueError("用户账户已被禁用")

        if self._verify_password(password, user.password_hash):
            # 更新最后登录时间
            self.update_last_login(user.id)
            return user

        return None

    @cache(ttl=3600)  # 缓存1小时
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.user_repository.find_by_id(user_id)

    @cache(ttl=1800)  # 缓存30分钟
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        criteria = {"username": username, "status": UserStatus.ACTIVE.value}
        users = self.user_repository.find_by_criteria(criteria)
        return users[0] if users else None

    @cache(ttl=1800)
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        criteria = {"email": email, "status": UserStatus.ACTIVE.value}
        users = self.user_repository.find_by_criteria(criteria)
        return users[0] if users else None

    def update_user_profile(self, user_id: int, profile_data: dict) -> bool:
        """更新用户档案"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # 更新允许的字段
        updatable_fields = ['first_name', 'last_name', 'phone']
        for field in updatable_fields:
            if field in profile_data:
                setattr(user, field, profile_data[field])

        self.user_repository.update(user)

        # 清除缓存
        self._clear_user_cache(user_id)

        return True

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        if not self._verify_password(old_password, user.password_hash):
            raise ValueError("原密码不正确")

        ValidationUtil.validate_password(new_password)

        user.password_hash = self._hash_password(new_password)
        self.user_repository.update(user)

        return True

    def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.status = UserStatus.INACTIVE
        self.user_repository.update(user)

        # 清除缓存
        self._clear_user_cache(user_id)

        return True

    def get_users_by_role(self, role: UserRole) -> List[User]:
        """根据角色获取用户列表"""
        criteria = {"role": role.value, "status": UserStatus.ACTIVE.value}
        return self.user_repository.find_by_criteria(criteria)

    def search_users(self, keyword: str, page: int = 1, page_size: int = 20) -> List[User]:
        """搜索用户"""
        keyword = keyword.strip()
        if not keyword:
            return []

        # 简化的搜索逻辑，实际实现应该使用更复杂的搜索条件
        criteria = {
            "status": UserStatus.ACTIVE.value
        }

        users = self.user_repository.find_by_criteria(criteria)

        # 在内存中进行过滤（实际应该在数据库层面进行）
        filtered_users = []
        for user in users:
            if (keyword.lower() in user.username.lower() or
                keyword.lower() in user.email.lower() or
                keyword.lower() in user.get_full_name().lower()):
                filtered_users.append(user)

        # 分页
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        return filtered_users[start_index:end_index]

    def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        from datetime import datetime

        user = self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.now()
            self.user_repository.update(user)

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salted_password = f"{self.password_salt}{password}"
        return hashlib.sha256(salted_password.encode()).hexdigest()

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == hashed_password

    def _clear_user_cache(self, user_id: int):
        """清除用户缓存"""
        # 这里应该调用缓存管理器清除相关缓存
        # 为了示例，只打印日志
        print(f"清除用户 {user_id} 的缓存")

    @PreDestroy
    def cleanup(self):
        """清理资源"""
        print("UserService 清理完成")

# 用户验证工具类
class UserValidator:
    """用户验证工具"""

    @staticmethod
    def validate_user_data(user_data: dict) -> List[str]:
        """验证用户数据"""
        errors = []

        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not user_data.get(field):
                errors.append(f"{field} 不能为空")

        username = user_data.get('username', '')
        if not (3 <= len(username) <= 20):
            errors.append("用户名长度必须在3-20个字符之间")

        if not StringUtil.is_valid_email(user_data.get('email', '')):
            errors.append("邮箱格式不正确")

        password = user_data.get('password', '')
        if len(password) < 6:
            errors.append("密码长度不能少于6个字符")

        return errors
```

这个完整项目示例展示了如何使用 Harmony Framework 构建一个结构良好、功能完整的电商系统。项目包含了：

1. **清晰的项目结构** - 按照标准的分层架构组织代码
2. **完整的配置管理** - 支持多环境配置和外部化配置
3. **丰富的数据模型** - 包含用户、产品、订单等核心业务模型
4. **灵活的数据访问层** - 基于仓储模式的数据访问
5. **完整的业务服务层** - 包含用户管理等核心业务逻辑
6. **AOP切面支持** - 日志、事务、缓存、安全等横切关注点
7. **生命周期管理** - 完整的应用启动和关闭流程

这个示例可以作为实际项目的参考模板，开发者可以根据具体需求进行调整和扩展。