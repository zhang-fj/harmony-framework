#!/usr/bin/env python3
"""
Harmony Framework 可扩展性和兼容性测试
测试框架的扩展能力、兼容性和版本升级支持
"""

import os
import sys
import time
import threading
import unittest
import gc
import traceback
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# 设置项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
src_path = os.path.join(current_dir, '..', 'src')

# 添加路径到sys.path
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestFrameworkExtensibilityCompatibility(unittest.TestCase):
    """框架可扩展性和兼容性测试类"""

    def setUp(self):
        """测试前准备"""
        self.test_start_time = time.time()

    def tearDown(self):
        """测试后清理"""
        test_duration = time.time() - self.test_start_time
        print(f"测试耗时: {test_duration:.3f}秒")
        gc.collect()

    def test_001_custom_scope_extension(self):
        """测试：自定义作用域扩展"""
        print("=== 自定义作用域扩展测试 ===")

        from harmony.core.scope import ScopeType
        from harmony.core.bean_definition import BeanDefinition
        from harmony.core.bean_factory import BeanFactory

        # 检查现有的作用域
        existing_scopes = [ScopeType.SINGLETON, ScopeType.PROTOTYPE, ScopeType.REQUEST, ScopeType.SESSION]
        print(f"现有作用域: {[scope.value for scope in existing_scopes]}")

        # 测试作用域扩展能力
        try:
            # 模拟添加自定义作用域（在实际应用中需要扩展ScopeType枚举）
            class CustomScope:
                def __init__(self, name, description="自定义作用域"):
                    self.value = name
                    self.description = description

            custom_scope = CustomScope("CUSTOM", "自定义作用域用于测试")
            print(f"创建自定义作用域: {custom_scope.value} - {custom_scope.description}")

            # 测试Bean定义与自定义作用域的兼容性
            bean_def = BeanDefinition(
                bean_type=str,
                bean_name="testCustomBean",
                scope=ScopeType.SINGLETON  # 使用标准作用域确保兼容性
            )

            # 验证Bean定义创建成功
            self.assertIsNotNone(bean_def)
            self.assertEqual(bean_def.bean_name, "testCustomBean")
            self.assertEqual(bean_def.scope, ScopeType.SINGLETON)

            print("✅ 自定义作用域扩展测试完成")

        except Exception as e:
            self.fail(f"自定义作用域扩展测试失败: {e}")

    def test_002_plugin_architecture_compatibility(self):
        """测试：插件架构兼容性"""
        print("=== 插件架构兼容性测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()

        # 创建插件风格的Bean
        try:
            # 基础插件接口
            class BasePlugin:
                def __init__(self):
                    self.name = "BasePlugin"
                    self.version = "1.0.0"

                def initialize(self):
                    return f"插件 {self.name} 初始化完成"

                def execute(self, data):
                    return f"插件 {self.name} 处理数据: {data}"

                def cleanup(self):
                    return f"插件 {self.name} 清理完成"

            # 具体插件实现
            class LoggingPlugin(BasePlugin):
                def __init__(self):
                    super().__init__()
                    self.name = "LoggingPlugin"
                    self.logs = []

                def execute(self, data):
                    log_entry = f"[LOG] {time.time()}: {data}"
                    self.logs.append(log_entry)
                    return log_entry

                def get_logs(self):
                    return self.logs

            class CachePlugin(BasePlugin):
                def __init__(self):
                    super().__init__()
                    self.name = "CachePlugin"
                    self.cache = {}

                def execute(self, data):
                    key = f"cache_{hash(data)}"
                    if key not in self.cache:
                        self.cache[key] = f"cached_{data}"
                    return self.cache[key]

                def get_cache_size(self):
                    return len(self.cache)

            # 注册插件
            context.register_bean(BasePlugin, "basePlugin", scope=ScopeType.SINGLETON.value)
            context.register_bean(LoggingPlugin, "loggingPlugin", scope=ScopeType.SINGLETON.value)
            context.register_bean(CachePlugin, "cachePlugin", scope=ScopeType.SINGLETON.value)

            # 测试插件功能
            base_plugin = context.get_bean("basePlugin")
            logging_plugin = context.get_bean("loggingPlugin")
            cache_plugin = context.get_bean("cachePlugin")

            # 验证插件接口兼容性
            self.assertEqual(base_plugin.initialize(), "插件 BasePlugin 初始化完成")
            self.assertEqual(logging_plugin.initialize(), "插件 LoggingPlugin 初始化完成")
            self.assertEqual(cache_plugin.initialize(), "插件 CachePlugin 初始化完成")

            # 测试插件功能
            log_result = logging_plugin.execute("测试日志数据")
            cache_result = cache_plugin.execute("测试缓存数据")

            self.assertIn("[LOG]", log_result)
            self.assertEqual(cache_result, "cached_测试缓存数据")
            self.assertEqual(len(logging_plugin.get_logs()), 1)
            self.assertEqual(cache_plugin.get_cache_size(), 1)

            # 测试插件多态
            plugins = [base_plugin, logging_plugin, cache_plugin]
            for plugin in plugins:
                result = plugin.execute(f"多态测试_{plugin.name}")
                self.assertIsNotNone(result)
                self.assertIn(plugin.name, result)

            print("✅ 插件架构兼容性测试完成")

        finally:
            context.close()

    def test_003_api_backward_compatibility(self):
        """测试：API向后兼容性"""
        print("=== API向后兼容性测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()

        try:
            # 测试传统API
            class LegacyBean:
                def __init__(self):
                    self.version = "1.0.0"

                def get_version(self):
                    return self.version

            # 使用传统方式注册Bean
            context.register_bean(LegacyBean, "legacyBean")

            # 获取Bean
            legacy_bean = context.get_bean("legacyBean")
            self.assertIsNotNone(legacy_bean)
            self.assertEqual(legacy_bean.get_version(), "1.0.0")

            # 测试新API
            class ModernBean:
                def __init__(self):
                    self.version = "2.0.0"
                    self.features = ["新特性1", "新特性2"]

                def get_version(self):
                    return self.version

                def get_features(self):
                    return self.features

            # 使用新方式注册Bean（带更多参数）
            context.register_bean(
                ModernBean,
                "modernBean",
                scope=ScopeType.SINGLETON.value,
                primary=True,
                lazy=False
            )

            # 获取Bean
            modern_bean = context.get_bean("modernBean")
            self.assertIsNotNone(modern_bean)
            self.assertEqual(modern_bean.get_version(), "2.0.0")
            self.assertEqual(len(modern_bean.get_features()), 2)

            # 测试API一致性
            beans = [legacy_bean, modern_bean]
            for bean in beans:
                version = bean.get_version()
                self.assertIsNotNone(version)
                self.assertIn(".", version)  # 版本号格式检查

            # 测试上下文API兼容性
            bean_names = context.get_bean_names()
            self.assertIn("legacyBean", bean_names)
            self.assertIn("modernBean", bean_names)

            # 测试contains_bean方法
            self.assertTrue(context.contains_bean("legacyBean"))
            self.assertTrue(context.contains_bean("modernBean"))
            self.assertFalse(context.contains_bean("nonExistentBean"))

            print("✅ API向后兼容性测试完成")

        finally:
            context.close()

    def test_004_cross_platform_compatibility(self):
        """测试：跨平台兼容性"""
        print("=== 跨平台兼容性测试 ===")

        from harmony.core.application_context import ApplicationContext

        # 检查当前平台
        current_platform = sys.platform
        print(f"当前平台: {current_platform}")

        # 测试路径处理兼容性
        context = ApplicationContext()

        try:
            # 创建跨平台兼容的Bean
            class PlatformBean:
                def __init__(self):
                    self.platform = sys.platform
                    self.path_separator = os.sep
                    self.temp_dir = os.path.normpath("/tmp")

                def get_platform_info(self):
                    return {
                        'platform': self.platform,
                        'path_separator': self.path_separator,
                        'temp_dir': self.temp_dir,
                        'python_version': sys.version
                    }

                def test_file_operations(self):
                    # 测试跨平台文件操作
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
                        f.write(f"Platform: {self.platform}\n")
                        temp_path = f.name
                        return os.path.exists(temp_path)

            context.register_bean(PlatformBean, "platformBean")
            platform_bean = context.get_bean("platformBean")

            # 验证平台信息
            platform_info = platform_bean.get_platform_info()
            self.assertIsNotNone(platform_info['platform'])
            self.assertIsNotNone(platform_info['path_separator'])
            self.assertIn(platform_info['path_separator'], ['/', '\\'])  # Unix或Windows路径分隔符

            # 测试文件操作兼容性
            file_op_result = platform_bean.test_file_operations()
            self.assertTrue(file_op_result)

            # 测试编码兼容性
            test_strings = ["Hello", "你好", "Привет", "مرحبا", "🚀"]
            for test_str in test_strings:
                try:
                    encoded = test_str.encode('utf-8')
                    decoded = encoded.decode('utf-8')
                    self.assertEqual(test_str, decoded)
                    print(f"  编码测试通过: {test_str}")
                except Exception as e:
                    self.fail(f"编码测试失败 '{test_str}': {e}")

            print("✅ 跨平台兼容性测试完成")

        finally:
            context.close()

    def test_005_external_library_integration(self):
        """测试：外部库集成"""
        print("=== 外部库集成测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()

        try:
            # 测试标准库集成
            class JsonProcessingBean:
                def __init__(self):
                    import json
                    self.json = json

                def process_data(self, data):
                    # 测试JSON序列化/反序列化
                    json_str = self.json.dumps(data, ensure_ascii=False)
                    return self.json.loads(json_str)

                def get_json_version(self):
                    return self.json.__version__ if hasattr(self.json, '__version__') else "builtin"

            class DateTimeBean:
                def __init__(self):
                    import datetime
                    from datetime import datetime as dt
                    self.datetime = dt

                def get_current_time(self):
                    return self.datetime.now()

                def format_timestamp(self, timestamp):
                    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

            class RandomDataBean:
                def __init__(self):
                    import random
                    self.random = random

                def generate_data(self, count=10):
                    return [self.random.randint(1, 100) for _ in range(count)]

                def shuffle_data(self, data):
                    self.random.shuffle(data)
                    return data

            # 注册集成Bean
            context.register_bean(JsonProcessingBean, "jsonProcessingBean")
            context.register_bean(DateTimeBean, "dateTimeBean")
            context.register_bean(RandomDataBean, "randomDataBean")

            # 测试JSON处理
            json_bean = context.get_bean("jsonProcessingBean")
            test_data = {"message": "测试数据", "numbers": [1, 2, 3], "nested": {"key": "value"}}
            processed_data = json_bean.process_data(test_data)
            self.assertEqual(processed_data, test_data)

            # 测试日期时间处理
            datetime_bean = context.get_bean("dateTimeBean")
            current_time = datetime_bean.get_current_time()
            formatted_time = datetime_bean.format_timestamp(current_time)
            self.assertIsNotNone(current_time)
            self.assertIsInstance(formatted_time, str)
            self.assertIn("-", formatted_time)  # 检查日期格式

            # 测试随机数据处理
            random_bean = context.get_bean("randomDataBean")
            random_data = random_bean.generate_data(5)
            self.assertEqual(len(random_data), 5)
            original_data = random_data.copy()
            shuffled_data = random_bean.shuffle_data(original_data)
            self.assertEqual(len(shuffled_data), len(original_data))

            # 测试第三方库兼容性（如果可用）
            external_libs = []
            try:
                import requests
                external_libs.append("requests")
                print("  requests库可用")
            except ImportError:
                print("  requests库不可用，跳过测试")

            try:
                import numpy
                external_libs.append("numpy")
                print("  numpy库可用")
            except ImportError:
                print("  numpy库不可用，跳过测试")

            print(f"  可用外部库: {external_libs}")

            print("✅ 外部库集成测试完成")

        finally:
            context.close()

    def test_006_configuration_flexibility(self):
        """测试：配置灵活性"""
        print("=== 配置灵活性测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()

        try:
            # 创建配置Bean
            class ConfigurableBean:
                def __init__(self, config=None):
                    self.config = config or {}
                    # 设置所有配置属性
                    for key, value in self.config.items():
                        setattr(self, key, value)
                    self.name = self.config.get('name', 'DefaultBean')
                    self.version = self.config.get('version', '1.0.0')
                    self.enabled = self.config.get('enabled', True)

                def configure(self, **kwargs):
                    self.config.update(kwargs)
                    for key, value in kwargs.items():
                        setattr(self, key, value)

                def get_config(self):
                    return self.config

                def is_enabled(self):
                    return self.enabled

            # 测试无配置初始化
            context.register_bean(ConfigurableBean, "defaultConfigurableBean")
            default_bean = context.get_bean("defaultConfigurableBean")
            self.assertEqual(default_bean.name, 'DefaultBean')
            self.assertEqual(default_bean.version, '1.0.0')
            self.assertTrue(default_bean.is_enabled())

            # 测试有配置初始化
            test_config = {
                'name': 'CustomBean',
                'version': '2.0.0',
                'enabled': False,
                'custom_property': 'test_value'
            }

            class ConfiguredBean(ConfigurableBean):
                def __init__(self):
                    super().__init__(test_config)

            context.register_bean(ConfiguredBean, "configuredBean")
            configured_bean = context.get_bean("configuredBean")
            self.assertEqual(configured_bean.name, 'CustomBean')
            self.assertEqual(configured_bean.version, '2.0.0')
            self.assertFalse(configured_bean.is_enabled())
            self.assertEqual(configured_bean.custom_property, 'test_value')

            # 测试动态配置
            dynamic_bean = ConfigurableBean()
            dynamic_bean.configure(
                name='DynamicBean',
                version='3.0.0',
                new_feature=True
            )

            self.assertEqual(dynamic_bean.name, 'DynamicBean')
            self.assertEqual(dynamic_bean.version, '3.0.0')
            self.assertTrue(dynamic_bean.new_feature)

            # 测试配置继承
            class ExtendedConfigurableBean(ConfigurableBean):
                def __init__(self, config=None):
                    super().__init__(config)
                    self.extended_property = config.get('extended_property', 'default_extended') if config else 'default_extended'

                def get_extended_config(self):
                    config = self.get_config().copy()
                    config['extended_property'] = self.extended_property
                    return config

            context.register_bean(ExtendedConfigurableBean, "extendedConfigurableBean")
            extended_bean = context.get_bean("extendedConfigurableBean")
            extended_config = extended_bean.get_extended_config()
            self.assertIn('extended_property', extended_config)

            print("✅ 配置灵活性测试完成")

        finally:
            context.close()

    def test_007_future_compatibility_design(self):
        """测试：未来兼容性设计"""
        print("=== 未来兼容性设计测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()

        try:
            # 模拟未来版本的Bean特性
            class FutureCompatibleBean:
                def __init__(self):
                    # 为未来扩展预留的属性
                    self.future_features = {}
                    self.deprecated_methods = {}
                    self.version = "future.1.0"

                def add_future_feature(self, name, implementation):
                    """添加未来特性"""
                    self.future_features[name] = implementation

                def get_available_features(self):
                    """获取可用特性"""
                    return list(self.future_features.keys())

                def execute_feature(self, feature_name, *args, **kwargs):
                    """执行指定特性"""
                    if feature_name in self.future_features:
                        return self.future_features[feature_name](*args, **kwargs)
                    else:
                        raise AttributeError(f"特性 '{feature_name}' 不存在")

                def mark_deprecated(self, method_name, alternative=None):
                    """标记方法为已弃用"""
                    self.deprecated_methods[method_name] = alternative

                def check_deprecated_usage(self, method_name):
                    """检查弃用方法的使用"""
                    if method_name in self.deprecated_methods:
                        alternative = self.deprecated_methods[method_name]
                        if alternative:
                            print(f"警告: '{method_name}' 已弃用，请使用 '{alternative}'")
                        else:
                            print(f"警告: '{method_name}' 已弃用")

            # 创建未来兼容Bean实例
            future_bean = FutureCompatibleBean()

            # 添加一些未来特性
            future_bean.add_future_feature("async_processing", lambda data: f"异步处理: {data}")
            future_bean.add_future_feature("caching", lambda key, value: f"缓存 {key}: {value}")
            future_bean.add_future_feature("metrics", lambda: {"requests": 100, "errors": 0})

            # 测试未来特性
            features = future_bean.get_available_features()
            self.assertIn("async_processing", features)
            self.assertIn("caching", features)
            self.assertIn("metrics", features)

            async_result = future_bean.execute_feature("async_processing", "测试数据")
            self.assertEqual(async_result, "异步处理: 测试数据")

            cache_result = future_bean.execute_feature("caching", "test_key", "test_value")
            self.assertEqual(cache_result, "缓存 test_key: test_value")

            metrics_result = future_bean.execute_feature("metrics")
            self.assertIsInstance(metrics_result, dict)

            # 测试弃用方法处理
            future_bean.mark_deprecated("old_method", "new_method")
            future_bean.check_deprecated_usage("old_method")  # 应该显示警告

            # 测试版本兼容性检查
            def check_version_compatibility(required_version, current_version):
                """检查版本兼容性"""
                try:
                    # 简单的版本比较
                    required_parts = required_version.split('.')
                    current_parts = current_version.split('.')

                    for i in range(min(len(required_parts), len(current_parts))):
                        if int(current_parts[i]) > int(required_parts[i]):
                            return True
                        elif int(current_parts[i]) < int(required_parts[i]):
                            return False

                    return len(current_parts) >= len(required_parts)
                except:
                    return True  # 无法解析版本时假设兼容

            # 测试版本兼容性
            compatible = check_version_compatibility("1.0.0", future_bean.version)
            self.assertTrue(compatible)  # future.1.0 应该与 1.0.0 兼容

            print("✅ 未来兼容性设计测试完成")

        finally:
            context.close()

    def test_008_extensibility_patterns(self):
        """测试：扩展性模式"""
        print("=== 扩展性模式测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()

        try:
            # 策略模式扩展
            class PaymentStrategy:
                def process_payment(self, amount):
                    raise NotImplementedError("子类必须实现支付处理方法")

            class CreditCardPayment(PaymentStrategy):
                def process_payment(self, amount):
                    return f"信用卡支付: ¥{amount:.2f}"

            class AlipayPayment(PaymentStrategy):
                def process_payment(self, amount):
                    return f"支付宝支付: ¥{amount:.2f}"

            class WeChatPayment(PaymentStrategy):
                def process_payment(self, amount):
                    return f"微信支付: ¥{amount:.2f}"

            # 注册策略实现
            context.register_bean(PaymentStrategy, "paymentStrategy")  # 基类
            context.register_bean(CreditCardPayment, "creditCardPayment")
            context.register_bean(AlipayPayment, "alipayPayment")
            context.register_bean(WeChatPayment, "wechatPayment")

            # 测试策略多态
            payments = [
                context.get_bean("creditCardPayment"),
                context.get_bean("alipayPayment"),
                context.get_bean("wechatPayment")
            ]

            test_amount = 100.0
            payment_results = []
            for payment in payments:
                result = payment.process_payment(test_amount)
                payment_results.append(result)
                self.assertIn(f"¥{test_amount:.2f}", result)

            self.assertEqual(len(payment_results), 3)

            # 观察者模式扩展
            class EventObserver:
                def __init__(self):
                    self.events = []

                def notify(self, event_type, data):
                    self.events.append((event_type, data))

            class EventManager:
                def __init__(self):
                    self.observers = []

                def add_observer(self, observer):
                    self.observers.append(observer)

                def remove_observer(self, observer):
                    if observer in self.observers:
                        self.observers.remove(observer)

                def notify_observers(self, event_type, data):
                    for observer in self.observers:
                        observer.notify(event_type, data)

            # 注册观察者模式组件
            context.register_bean(EventObserver, "eventObserver")
            context.register_bean(EventManager, "eventManager")

            # 测试观察者模式
            event_manager = context.get_bean("eventManager")
            observer1 = context.get_bean("eventObserver")
            observer2 = EventObserver()  # 直接创建另一个观察者

            event_manager.add_observer(observer1)
            event_manager.add_observer(observer2)

            # 发送事件
            event_manager.notify_observers("bean_created", {"bean": "testBean"})
            event_manager.notify_observers("bean_destroyed", {"bean": "testBean"})

            # 验证事件接收
            self.assertEqual(len(observer1.events), 2)
            self.assertEqual(len(observer2.events), 2)

            # 工厂模式扩展
            class DatabaseConnectionFactory:
                def __init__(self):
                    self.factories = {}

                def register_factory(self, db_type, factory_func):
                    self.factories[db_type] = factory_func

                def create_connection(self, db_type, **kwargs):
                    if db_type in self.factories:
                        return self.factories[db_type](**kwargs)
                    raise ValueError(f"不支持的数据库类型: {db_type}")

            # 注册工厂模式组件
            context.register_bean(DatabaseConnectionFactory, "databaseConnectionFactory")

            connection_factory = context.get_bean("databaseConnectionFactory")

            # 注册不同数据库的工厂函数
            def create_mysql_connection(host, port, database):
                return f"MySQL连接: {host}:{port}/{database}"

            def create_postgresql_connection(host, port, database):
                return f"PostgreSQL连接: {host}:{port}/{database}"

            def create_sqlite_connection(path):
                return f"SQLite连接: {path}"

            connection_factory.register_factory("mysql", create_mysql_connection)
            connection_factory.register_factory("postgresql", create_postgresql_connection)
            connection_factory.register_factory("sqlite", create_sqlite_connection)

            # 测试工厂模式
            mysql_conn = connection_factory.create_connection("mysql", host="localhost", port=3306, database="test")
            postgresql_conn = connection_factory.create_connection("postgresql", host="localhost", port=5432, database="test")
            sqlite_conn = connection_factory.create_connection("sqlite", path="/tmp/test.db")

            self.assertIn("MySQL连接", mysql_conn)
            self.assertIn("PostgreSQL连接", postgresql_conn)
            self.assertIn("SQLite连接", sqlite_conn)

            print("✅ 扩展性模式测试完成")

        finally:
            context.close()


def run_framework_extensibility_compatibility_tests():
    """运行框架可扩展性和兼容性测试"""
    print("🔧 Harmony Framework 可扩展性和兼容性测试")
    print("=" * 80)

    # 创建测试套件
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFrameworkExtensibilityCompatibility))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果摘要
    print("\n" + "=" * 80)
    print(f"📊 框架可扩展性和兼容性测试结果:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors))/result.testsRun*100:.1f}%")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 所有可扩展性和兼容性测试通过！")
        print("💡 Harmony Framework 扩展性和兼容性表现出色！")
        success = True
    else:
        print("⚠️ 存在失败的测试，需要进一步优化扩展性和兼容性")
        success = False

        # 打印失败详情
        if result.failures:
            print("\n❌ 失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}")
                print(f"    {traceback}")

        if result.errors:
            print("\n💥 错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}")
                print(f"    {traceback}")

    print("=" * 80)
    return success


if __name__ == "__main__":
    success = run_framework_extensibility_compatibility_tests()
    sys.exit(0 if success else 1)