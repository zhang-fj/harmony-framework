#!/usr/bin/env python3
"""
Harmony Framework 压力测试和边界测试
测试框架在极端条件下的表现
"""

import os
import sys
import time
import threading
import unittest
import gc
import weakref
import psutil
import signal
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string

# 设置项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
src_path = os.path.join(current_dir, '..', 'src')

# 添加路径到sys.path
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestStressAndBoundary(unittest.TestCase):
    """压力测试和边界测试类"""

    def setUp(self):
        """测试前准备"""
        self.test_start_time = time.time()
        self.process = psutil.Process()

    def tearDown(self):
        """测试后清理"""
        test_duration = time.time() - self.test_start_time
        print(f"测试耗时: {test_duration:.3f}秒")
        # 强制垃圾回收
        gc.collect()

    def get_memory_usage(self):
        """获取当前内存使用情况"""
        memory_info = self.process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': self.process.memory_percent()
        }

    def test_001_massive_bean_registration(self):
        """测试：大规模Bean注册"""
        print("=== 大规模Bean注册测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()
        initial_memory = self.get_memory_usage()
        print(f"初始内存: {initial_memory['rss']:.2f}MB")

        # 大量Bean注册测试
        bean_count = 10000
        start_time = time.time()

        for i in range(bean_count):
            class_name = f"StressBean{i}"
            # 动态创建类
            stress_class = type(class_name, (), {
                'get_id': lambda self, idx=i: idx,
                'get_name': lambda self: f"StressBean{i}"
            })
            context.register_bean(stress_class, f"stressBean{i}")

        registration_time = time.time() - start_time
        final_memory = self.get_memory_usage()
        print(f"注册{bean_count}个Bean用时: {registration_time:.3f}秒")
        print(f"注册后内存: {final_memory['rss']:.2f}MB (增加{final_memory['rss'] - initial_memory['rss']:.2f}MB)")

        # 验证注册成功
        self.assertEqual(len(context.get_bean_names()), bean_count, "所有Bean应该成功注册")

        # 性能断言
        self.assertLess(registration_time, 10.0, "大规模注册应该性能良好")
        self.assertLess(final_memory['rss'] - initial_memory['rss'], 500, "内存增长应该合理")

        print("✅ 大规模Bean注册测试完成")

    def test_002_concurrent_massive_operations(self):
        """测试：并发大规模操作"""
        print("=== 并发大规模操作测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()
        operations_per_thread = 100
        thread_count = 20

        def worker_thread(thread_id):
            """工作线程"""
            results = []
            for i in range(operations_per_thread):
                try:
                    # 创建并注册Bean
                    class_name = f"ConcurrentBean{thread_id}_{i}"
                    concurrent_class = type(class_name, (), {
                        'get_info': lambda self, tid=thread_id, idx=i: f"Thread{tid}-Bean{idx}"
                    })
                    bean_name = f"concurrentBean{thread_id}_{i}"
                    context.register_bean(concurrent_class, bean_name)

                    # 获取Bean
                    bean = context.get_bean(bean_name)
                    results.append(bean.get_info())

                except Exception as e:
                    results.append(f"Error: {e}")

            return results

        # 并发执行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(thread_count)]
            all_results = []
            for future in as_completed(futures):
                try:
                    results = future.result(timeout=30)
                    all_results.extend(results)
                except Exception as e:
                    print(f"线程执行异常: {e}")

        execution_time = time.time() - start_time
        total_operations = thread_count * operations_per_thread
        successful_ops = len([r for r in all_results if not r.startswith("Error:")])

        print(f"并发执行{total_operations}个操作用时: {execution_time:.3f}秒")
        print(f"成功操作: {successful_ops}/{total_operations}")
        print(f"操作速率: {total_operations/execution_time:.0f} ops/sec")

        # 性能断言
        self.assertGreater(successful_ops, total_operations * 0.95, "并发成功率应该很高")
        self.assertLess(execution_time, 15.0, "并发执行应该在合理时间内完成")

        print("✅ 并发大规模操作测试完成")

    def test_003_deep_dependency_chains(self):
        """测试：深层依赖链"""
        print("=== 深层依赖链测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()
        max_depth = 50

        # 创建深层依赖链
        beans = []
        for i in range(max_depth):
            class_name = f"DeepBean{i}"

            # 每个Bean依赖前一个Bean
            if i > 0:
                parent_class = beans[i-1]

                # 创建带依赖的类 - 使用闭包捕获正确的class_name
                def create_deep_bean(idx, name):
                    class DeepBean:
                        def __init__(self):
                            self.parent = None
                            self.name = name
                            self.depth = idx

                        def set_parent(self, parent):
                            self.parent = parent

                        def get_chain_length(self):
                            if self.parent:
                                return 1 + self.parent.get_chain_length()
                            return 1

                        def get_root_name(self):
                            if self.parent:
                                return self.parent.get_root_name()
                            return self.name
                    return DeepBean

                beans.append(create_deep_bean(i, class_name))
            else:
                # 根节点类
                def create_root_bean(idx, name):
                    class DeepBean:
                        def __init__(self):
                            self.name = name
                            self.depth = idx

                        def get_chain_length(self):
                            return 1

                        def get_root_name(self):
                            return self.name
                    return DeepBean

                beans.append(create_root_bean(i, class_name))

        # 注册所有Bean
        for i, bean_class in enumerate(beans):
            bean_name = f"deepBean{i}"
            context.register_bean(bean_class, bean_name)

        # 手动构建依赖链
        for i in range(1, max_depth):
            parent = context.get_bean(f"deepBean{i-1}")
            child = context.get_bean(f"deepBean{i}")
            child.set_parent(parent)

        # 测试依赖链
        root_bean = context.get_bean("deepBean0")
        deepest_bean = context.get_bean(f"deepBean{max_depth-1}")

        chain_length = deepest_bean.get_chain_length()
        root_name = deepest_bean.get_root_name()

        self.assertEqual(chain_length, max_depth, "依赖链长度应该正确")
        self.assertEqual(root_name, "DeepBean0", "根节点应该正确")

        # 性能测试 - 遍历依赖链
        start_time = time.time()
        for _ in range(100):
            chain_length = deepest_bean.get_chain_length()
        traversal_time = time.time() - start_time

        print(f"深层依赖链({max_depth}层)遍历100次用时: {traversal_time:.3f}秒")
        self.assertLess(traversal_time, 1.0, "深层依赖链遍历应该高效")

        print("✅ 深层依赖链测试完成")

    def test_004_memory_pressure_resilience(self):
        """测试：内存压力下的稳定性"""
        print("=== 内存压力下的稳定性测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()
        initial_memory = self.get_memory_usage()
        print(f"初始内存: {initial_memory['rss']:.2f}MB")

        # 创建大量原型Bean来测试内存压力
        prototype_beans = []
        batch_size = 100
        total_batches = 50

        try:
            for batch in range(total_batches):
                batch_beans = []
                for i in range(batch_size):
                    class_name = f"MemoryBean{batch}_{i}"
                    memory_class = type(class_name, (), {
                        'data': 'x' * 1024,  # 1KB data
                        'batch': batch,
                        'index': i,
                        'get_size': lambda self: len(self.data)
                    })
                    bean_name = f"memoryBean{batch}_{i}"
                    context.register_bean(memory_class, bean_name, scope=ScopeType.PROTOTYPE.value)

                    # 立即获取Bean创建实例
                    bean = context.get_bean(bean_name)
                    batch_beans.append(bean)

                prototype_beans.extend(batch_beans)

                # 检查内存使用
                if batch % 10 == 0:
                    current_memory = self.get_memory_usage()
                    print(f"批次{batch}: 内存 {current_memory['rss']:.2f}MB (已创建{len(prototype_beans)}个Bean)")

                    # 内存压力检查
                    if current_memory['rss'] > initial_memory['rss'] + 1000:  # 1GB限制
                        print(f"内存使用达到{current_memory['rss']:.2f}MB，停止创建")
                        break

        except MemoryError:
            print("内存不足，测试通过（正确处理了内存错误）")

        finally:
            # 清理引用
            prototype_beans.clear()
            gc.collect()

        final_memory = self.get_memory_usage()
        print(f"测试后内存: {final_memory['rss']:.2f}MB")
        print(f"总创建Bean数: {len(prototype_beans)}")

        # 验证清理后内存恢复
        self.assertLess(final_memory['rss'] - initial_memory['rss'], 200, "内存应该合理释放")

        print("✅ 内存压力下的稳定性测试完成")

    def test_005_rapid_bean_creation_destruction(self):
        """测试：快速Bean创建和销毁"""
        print("=== 快速Bean创建和销毁测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        iterations = 1000
        creation_times = []
        destruction_times = []

        for i in range(iterations):
            # 测试Bean创建时间
            start_time = time.time()

            context = ApplicationContext()  # 每次新context确保完全清理

            class TestBean:
                def __init__(self, value):
                    self.value = value
                    self.created_time = time.time()

                def cleanup(self):
                    pass

            context.register_bean(TestBean, "testBean")
            bean = context.get_bean("testBean")

            creation_time = time.time() - start_time
            creation_times.append(creation_time)

            # 测试销毁时间
            start_time = time.time()
            context.close()
            del bean
            del context
            gc.collect()

            destruction_time = time.time() - start_time
            destruction_times.append(destruction_time)

            if i % 100 == 0:
                print(f"进度: {i}/{iterations} - 平均创建时间: {sum(creation_times[-100:])/min(100, len(creation_times)):.6f}s")

        # 统计分析
        avg_creation_time = sum(creation_times) / len(creation_times)
        avg_destruction_time = sum(destruction_times) / len(destruction_times)
        max_creation_time = max(creation_times)
        min_creation_time = min(creation_times)

        print(f"平均创建时间: {avg_creation_time:.6f}s")
        print(f"平均销毁时间: {avg_destruction_time:.6f}s")
        print(f"最大创建时间: {max_creation_time:.6f}s")
        print(f"最小创建时间: {min_creation_time:.6f}s")

        # 性能断言
        self.assertLess(avg_creation_time, 0.01, "Bean创建应该足够快")
        self.assertLess(max_creation_time, 0.1, "即使最坏情况创建时间也应该合理")

        print("✅ 快速Bean创建和销毁测试完成")

    def test_006_error_resilience_under_stress(self):
        """测试：压力下的错误恢复能力"""
        print("=== 压力下的错误恢复能力测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.exceptions.harmony_exceptions import NoSuchBeanDefinitionException

        context = ApplicationContext()

        # 先注册一些正常的Bean
        for i in range(100):
            class_name = f"NormalBean{i}"
            normal_class = type(class_name, (), {'id': i})
            context.register_bean(normal_class, f"normalBean{i}")

        # 并发错误注入测试
        def error_injection_worker(worker_id):
            errors = 0
            successes = 0

            for i in range(50):
                try:
                    # 尝试获取不存在的Bean
                    context.get_bean(f"nonExistentBean{worker_id}_{i}")
                except NoSuchBeanDefinitionException:
                    errors += 1
                except Exception as e:
                    print(f"意外错误: {e}")
                    errors += 1
                else:
                    successes += 1

                # 尝试获取正常Bean
                try:
                    bean = context.get_bean(f"normalBean{i % 100}")
                    if bean is not None:
                        successes += 1
                except Exception as e:
                    errors += 1

            return {"worker_id": worker_id, "errors": errors, "successes": successes}

        # 并发执行错误注入
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(error_injection_worker, i) for i in range(10)]
            results = []

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"Worker执行异常: {e}")

        # 分析结果
        total_errors = sum(r["errors"] for r in results)
        total_successes = sum(r["successes"] for r in results)
        expected_errors = len(results) * 50  # 每个worker应该有50个预期的错误

        print(f"总错误数: {total_errors} (预期: {expected_errors})")
        print(f"总成功数: {total_successes}")
        print(f"错误处理准确率: {total_errors/expected_errors*100:.1f}%")

        # 验证错误处理能力
        self.assertGreater(total_errors, expected_errors * 0.9, "应该正确处理大部分错误")
        self.assertGreater(total_successes, 0, "正常的操作应该成功")

        print("✅ 压力下的错误恢复能力测试完成")

    def test_007_extreme_concurrent_scenarios(self):
        """测试：极端并发场景"""
        print("=== 极端并发场景测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()

        # 注册各种类型的Bean
        for i in range(50):
            # 单例Bean
            class_name = f"SingletonBean{i}"
            singleton_class = type(class_name, (), {
                'get_type': lambda self: 'singleton',
                'get_id': lambda self, idx=i: idx
            })
            context.register_bean(singleton_class, f"singletonBean{i}", scope=ScopeType.SINGLETON.value)

            # 原型Bean
            class_name = f"PrototypeBean{i}"
            prototype_class = type(class_name, (), {
                'get_type': lambda self: 'prototype',
                'get_id': lambda self, idx=i: idx
            })
            context.register_bean(prototype_class, f"prototypeBean{i}", scope=ScopeType.PROTOTYPE.value)

        def extreme_worker(worker_id, iterations=1000):
            """极端工作负载"""
            operations = []

            for i in range(iterations):
                try:
                    # 随机选择Bean类型
                    bean_type = random.choice(['singleton', 'prototype'])
                    bean_index = random.randint(0, 49)
                    bean_name = f"{bean_type}Bean{bean_index}"

                    # 获取Bean
                    bean = context.get_bean(bean_name)

                    # 执行操作
                    bean_type_info = bean.get_type()
                    bean_id = bean.get_id()

                    operations.append(f"Worker{worker_id}: {bean_type_info}-{bean_id}")

                    # 随机延迟，模拟真实负载
                    if random.random() < 0.01:  # 1%的概率延迟
                        time.sleep(0.001)

                except Exception as e:
                    operations.append(f"Worker{worker_id} Error: {e}")

            return operations

        # 极端并发测试
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(extreme_worker, i, 500) for i in range(20)]
            all_operations = []

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    all_operations.extend(result)
                except Exception as e:
                    print(f"极端工作负载异常: {e}")

        execution_time = time.time() - start_time
        total_operations = len(all_operations)
        error_count = len([op for op in all_operations if "Error" in op])
        success_count = total_operations - error_count

        print(f"极端并发测试完成:")
        print(f"  总操作数: {total_operations}")
        print(f"  成功操作: {success_count}")
        print(f"  失败操作: {error_count}")
        print(f"  执行时间: {execution_time:.3f}s")
        print(f"  操作速率: {total_operations/execution_time:.0f} ops/sec")
        print(f"  成功率: {success_count/total_operations*100:.2f}%")

        # 验证极端场景下的稳定性
        self.assertGreater(success_count, total_operations * 0.95, "极端并发下应该保持高成功率")
        self.assertLess(error_count, total_operations * 0.05, "错误率应该很低")

        print("✅ 极端并发场景测试完成")


def run_stress_and_boundary_tests():
    """运行压力测试和边界测试"""
    print("🚀 Harmony Framework 压力测试和边界测试")
    print("=" * 80)

    # 创建测试套件
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestStressAndBoundary))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果摘要
    print("\n" + "=" * 80)
    print(f"📊 压力测试和边界测试结果:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors))/result.testsRun*100:.1f}%")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 所有压力测试和边界测试通过！")
        print("💡 Harmony Framework 在极端条件下表现出色！")
        success = True
    else:
        print("⚠️ 存在失败的测试，需要进一步优化")
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
    success = run_stress_and_boundary_tests()
    sys.exit(0 if success else 1)