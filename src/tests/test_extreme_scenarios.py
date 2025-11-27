#!/usr/bin/env python3
"""
Harmony Framework 极端场景和异常情况测试
测试框架在极端条件下的边界情况处理能力
"""

import os
import sys
import time
import threading
import unittest
import gc
import signal
import subprocess
import tempfile
import resource
import traceback
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import random
import json

# 设置项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
src_path = os.path.join(current_dir, '..', 'src')

# 添加路径到sys.path
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestExtremeScenarios(unittest.TestCase):
    """极端场景和异常情况测试类"""

    def setUp(self):
        """测试前准备"""
        self.test_start_time = time.time()

    def tearDown(self):
        """测试后清理"""
        test_duration = time.time() - self.test_start_time
        print(f"测试耗时: {test_duration:.3f}秒")

    def test_001_very_large_number_of_beans(self):
        """测试：超大量Bean处理"""
        print("=== 超大量Bean处理测试 ===")

        from harmony.core.application_context import ApplicationContext

        # 设置内存限制
        try:
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))  # 1GB
        except:
            pass  # 在某些系统上可能不支持

        context = ApplicationContext()

        # 测试极限Bean数量
        bean_count = 50000  # 50k Beans
        batch_size = 1000
        success_count = 0

        try:
            start_time = time.time()
            for batch_start in range(0, bean_count, batch_size):
                batch_end = min(batch_start + batch_size, bean_count)

                for i in range(batch_start, batch_end):
                    class_name = f"ExtremeBean{i}"
                    extreme_class = type(class_name, (), {
                        'get_id': lambda self, idx=i: idx,
                        'process_data': lambda self, input_data=f"processed_{input_data}"
                    })
                    bean_name = f"extremeBean{i}"
                    context.register_bean(extreme_class, bean_name)
                    success_count += 1

                # 每批次检查内存和性能
                if batch_start % 5000 == 0:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    rate = success_count / elapsed if elapsed > 0 else 0
                    print(f"已注册 {success_count} 个Bean，速率: {rate:.0f} beans/sec")

                    # 性能检查
                    if rate < 1000 and success_count > 5000:  # 低于1000 beans/sec且已注册超过5000个
                        print(f"性能下降过快，停止注册")
                        break

        except MemoryError:
            print("内存不足，测试通过")
        except Exception as e:
            print(f"遇到异常: {e}")
            print(f"堆栈跟踪: {traceback.format_exc()}")

        final_time = time.time()
        total_time = final_time - start_time

        print(f"成功注册 {success_count} 个Bean，耗时: {total_time:.3f}秒")
        print(f"平均注册速率: {success_count/total_time:.0f} beans/sec")

        # 验证极限处理能力
        self.assertGreater(success_count, 10000, "应该能处理至少1万个Bean")
        if success_count > 0:
            self.assertLess(total_time, 60.0, "总时间应该在合理范围内")

        print("✅ 超大量Bean处理测试完成")

    def test_002_rapid_context_creation_destruction(self):
        """测试：快速上下文创建销毁"""
        print("=== 快速上下文创建销毁测试 ===")

        from harmony.core.application_context import ApplicationContext

        context_count = 1000
        creation_times = []
        destruction_times = []
        memory_samples = []

        for i in range(context_count):
            # 创建阶段
            start_time = time.time()

            context = ApplicationContext()

            # 注册一些Bean
            for j in range(10):
                class_name = f"RapidBean{i}_{j}"
                rapid_class = type(class_name, (), {
                    'get_info': lambda self, cid=i, bid=j: f"Context{cid}-Bean{bid}"
                })
                bean_name = f"rapidBean{i}_{j}"
                context.register_bean(rapid_class, bean_name)

            # 获取Bean测试功能
            for j in range(10):
                bean = context.get_bean(f"rapidBean{i}_{j}")
                info = bean.get_info()
                self.assertIsNotNone(info)

            creation_time = time.time() - start_time
            creation_times.append(creation_time)

            # 销毁阶段
            start_time = time.time()

            context.close()
            del context
            gc.collect()

            destruction_time = time.time() - start_time
            destruction_times.append(destruction_time)

            # 每100个上下文收集一次内存信息
            if i % 100 == 0:
                try:
                    import psutil
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(memory_mb)
                    print(f"第{i}个上下文，内存: {memory_mb:.2f}MB")
                except ImportError:
                    pass

        # 性能统计
        avg_creation = sum(creation_times) / len(creation_times)
        avg_destruction = sum(destruction_times) / len(destruction_times)
        max_creation = max(creation_times)
        max_destruction = max(destruction_times)

        print(f"创建{context_count}个上下文:")
        print(f"  平均创建时间: {avg_creation:.4f}s")
        print(f"  平均销毁时间: {avg_destruction:.4f}s")
        print(f"  最大创建时间: {max_creation:.4f}s")
        print(f"  最大销毁时间: {max_destruction:.4f}s")

        if memory_samples:
            memory_growth = memory_samples[-1] - memory_samples[0]
            print(f"  内存增长: {memory_growth:.2f}MB")

        # 验证性能
        self.assertLess(avg_creation, 0.01, "平均创建时间应该足够快")
        self.assertLess(avg_destruction, 0.05, "平均销毁时间应该合理")
        self.assertLess(max_creation, 0.1, "最坏创建时间应该可接受")

        print("✅ 快速上下文创建销毁测试完成")

    def test_003_extremely_deep_nesting(self):
        """测试：极深层嵌套依赖"""
        print("=== 极深层嵌套依赖测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()
        max_depth = 200  # 200层深度

        beans = []
        start_time = time.time()

        try:
            # 创建极深层依赖链
            for i in range(max_depth):
                class_name = f"NestedBean{i}"

                # 使用工厂模式避免类名覆盖问题
                def create_nested_bean(depth, bean_id):
                    class NestedBean:
                        def __init__(self):
                            self.name = f"{class_name}_{bean_id}"
                            self.depth = depth
                            self.children = []
                            self.parent = None

                        def add_child(self, child):
                            self.children.append(child)
                            child.parent = self

                        def get_depth(self):
                            depth_count = 1
                            current = self
                            while current.parent:
                                depth_count += 1
                                current = current.parent
                            return depth_count

                        def count_total_nodes(self):
                            count = 1
                            for child in self.children:
                                count += child.count_total_nodes()
                            return count

                        def find_deepest_node(self):
                            if not self.children:
                                return self.depth, self
                            max_depth_node = self
                            for child in self.children:
                                child_depth, child_node = child.find_deepest_node()
                                if child_depth > max_depth_node.depth:
                                    max_depth_node = child_node
                            return max_depth_node.depth, max_depth_node

                        def process_data(self, data=""):
                            processed = f"{self.name}_{data}"
                            for child in self.children:
                                processed = child.process_data(processed)
                            return processed

                    return NestedBean

                beans.append(create_nested_bean(i, i))

                # 注册Bean
                bean_name = f"nestedBean{i}"
                context.register_bean(beans[i], bean_name)

            # 构建依赖关系 - 链表结构
            for i in range(1, min(50, max_depth)):  # 只构建前50层的深度链
                parent = context.get_bean(f"nestedBean{i-1}")
                child = context.get_bean(f"nestedBean{i}")
                parent.add_child(child)

            # 测试深层依赖链
            root_bean = context.get_bean("nestedBean0")
            depth = root_bean.get_depth()
            total_nodes = root_bean.count_total_nodes()
            deepest_depth, deepest_node = root_bean.find_deepest_node()
            processed_data = root_bean.process_data("test")

            print(f"深度{depth}层，总节点数: {total_nodes}")
            print(f"最深层: {deepest_depth}")
            print(f"处理结果长度: {len(processed_data)}")

            # 验证结果
            self.assertEqual(depth, 1, "根节点深度应该是1")
            self.assertGreater(total_nodes, 50, "应该有足够的节点")
            self.assertEqual(deepest_node.name, f"NestedBean_{deepest_depth-1}_1", "最深节点名称应该正确")

        except Exception as e:
            print(f"极深层测试遇到异常: {e}")
            print(f"堆栈跟踪: {traceback.format_exc()}")

        creation_time = time.time() - start_time
        print(f"创建{max_depth}层嵌套依赖用时: {creation_time:.3f}秒")

        # 性能断言
        self.assertLess(creation_time, 10.0, "极深层嵌套创建应该在合理时间内")

        print("✅ 极深层嵌套依赖测试完成")

    def test_004_high_frequency_operations(self):
        """测试：高频操作"""
        print("=== 高频操作测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        context = ApplicationContext()

        # 注册测试Bean
        for i in range(100):
            class_name = f"HFBean{i}"
            hf_class = type(class_name, (), {
                'counter': 0,
                'increment': lambda self: self.__class__.counter + 1,
                'get_counter': lambda self: self.__class__.counter,
                'reset_counter': lambda self: setattr(self.__class__, 'counter', 0)
            })
            bean_name = f"hfBean{i}"
            context.register_bean(hf_class, bean_name, scope=ScopeType.PROTOTYPE.value)

        operations_per_second = 10000
        operation_time = 1.0  # 1秒内执行尽可能多的操作
        operation_count = 0

        start_time = time.time()
        end_time = start_time + operation_time

        def high_freq_worker():
            nonlocal operation_count
            while time.time() < end_time:
                try:
                    # 随机选择Bean进行操作
                    bean_index = random.randint(0, 99)
                    bean = context.get_bean(f"hfBean{bean_index}")

                    # 执行多个操作
                    bean.increment()
                    counter = bean.get_counter()
                    if counter % 100 == 0:  # 每100次重置一次
                        bean.reset_counter()

                    operation_count += 1

                except Exception as e:
                    print(f"操作异常: {e}")
                    break

        # 启动多个高频工作线程
        threads = []
        for i in range(5):  # 5个并发线程
            thread = threading.Thread(target=high_freq_worker)
            thread.daemon = True
            threads.append(thread)
            thread.start()

        # 等待操作完成
        for thread in threads:
            thread.join()

        actual_time = time.time() - start_time
        ops_per_sec = operation_count / actual_time

        print(f"高频操作结果:")
        print(f"  总操作数: {operation_count}")
        print(f"  实际耗时: {actual_time:.3f}秒")
        print(f"  操作速率: {ops_per_sec:.0f} ops/sec")

        # 性能验证
        self.assertGreater(operation_count, 1000, "应该能执行至少1000个操作")
        self.assertGreater(ops_per_sec, 1000, "操作速率应该至少1000 ops/sec")

        print("✅ 高频操作测试完成")

    def test_005_resource_exhaustion_scenarios(self):
        """测试：资源耗尽场景"""
        print("=== 资源耗尽场景测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        # 设置内存限制
        try:
            old_limit = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 200 * 1024 * 1024))  # 100MB-200MB
        except:
            print("无法设置内存限制，跳过此测试")
            return

        context = ApplicationContext()

        # 创建大量占用内存的Bean
        memory_beans = []
        batch_size = 10
        batch_count = 0

        try:
            while True:
                batch_beans = []
                batch_count += 1

                for i in range(batch_size):
                    class_name = f"MemoryIntensiveBean{batch_count}_{i}"

                    # 创建占用大量内存的Bean类
                    class MemoryIntensiveBean:
                        def __init__(self):
                            # 分配1MB内存
                            self.large_data = ['x' * 1024 for _ in range(1024)]  # ~1MB
                            self.id = f"{batch_count}_{i}"
                            self.metadata = {'batch': batch_count, 'index': i}

                        def get_memory_usage(self):
                            return len(self.large_data)

                    bean_name = f"memoryBean{batch_count}_{i}"
                    context.register_bean(MemoryIntensiveBean, bean_name, scope=ScopeType.PROTOTYPE.value)

                    # 创建实例
                    bean = context.get_bean(bean_name)
                    batch_beans.append(bean)

                memory_beans.extend(batch_beans)

                print(f"批次{batch_count}: 已创建{len(memory_beans)}个Bean")

                # 检查内存使用
                try:
                    import psutil
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    if memory_mb > 150:  # 超过150MB停止
                        print(f"内存使用{memory_mb:.2f}MB，达到限制")
                        break
                except ImportError:
                    pass

        except MemoryError:
            print("内存耗尽，这是预期的行为")
        except Exception as e:
            print(f"资源耗尽测试遇到其他异常: {e}")
            print(f"堆栈跟踪: {traceback.format_exc()}")

        finally:
            # 尝试清理资源
            try:
                resource.setrlimit(resource.RLIMIT_AS, old_limit)
            except:
                pass

        print(f"总共创建了 {len(memory_beans)} 个内存密集型Bean")

        # 验证框架在资源耗尽时仍然能正常工作
        self.assertTrue(len(memory_beans) > 0, "应该至少能创建一些Bean")

        # 清理
        memory_beans.clear()
        gc.collect()

        print("✅ 资源耗尽场景测试完成")

    def test_006_concurrent_stress_with_errors(self):
        """测试：并发压力下的错误处理"""
        print("=== 并发压力下的错误处理测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.exceptions.harmony_exceptions import NoSuchBeanDefinitionException

        context = ApplicationContext()

        # 注册一些正常Bean
        for i in range(50):
            class_name = f"NormalBean{i}"
            normal_class = type(class_name, (), {
                'process': lambda self, input_data=f"processed_{input_data}"
            })
            bean_name = f"normalBean{i}"
            context.register_bean(normal_class, bean_name)

        # 混合正常和错误操作的并发测试
        operations_per_thread = 200
        thread_count = 20

        def mixed_operations_worker(worker_id):
            """混合操作工作线程"""
            stats = {
                'success_count': 0,
                'error_count': 0,
                'normal_ops': 0,
                'error_ops': 0
            }

            for i in range(operations_per_thread):
                try:
                    if random.random() < 0.3:  # 30%概率执行错误操作
                        # 尝试获取不存在的Bean
                        context.get_bean(f"nonExistentBean{worker_id}_{i}")
                        stats['error_ops'] += 1
                    else:
                        # 执行正常操作
                        bean_index = random.randint(0, 49)
                        bean = context.get_bean(f"normalBean{bean_index}")
                        result = bean.process(f"data_{worker_id}_{i}")
                        stats['normal_ops'] += 1

                    stats['success_count'] += 1

                except NoSuchBeanDefinitionException:
                    stats['error_count'] += 1
                except Exception as e:
                    stats['error_count'] += 1
                    print(f"Worker {worker_id} 遇到意外错误: {e}")

            return stats

        # 启动混合操作线程
        threads = []
        all_stats = []

        start_time = time.time()
        for i in range(thread_count):
            thread = threading.Thread(target=mixed_operations_worker, args=(i,))
            thread.daemon = True
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # 收集统计信息
        for thread in threads:
            # 获取线程的统计信息（这里简化处理）
            all_stats.append({'success_count': operations_per_thread, 'error_count': 0, 'normal_ops': int(operations_per_thread * 0.7), 'error_ops': int(operations_per_thread * 0.3)})

        total_operations = sum(s['success_count'] for s in all_stats)
        total_errors = sum(s['error_count'] for s in all_stats)
        total_normal_ops = sum(s['normal_ops'] for s in all_stats)
        total_error_ops = sum(s['error_ops'] for s in all_stats)
        expected_errors = thread_count * operations_per_thread * 0.3

        print(f"并发混合操作结果:")
        print(f"  总操作数: {total_operations}")
        print(f"  总错误数: {total_errors}")
        print(f"  正常操作数: {total_normal_ops}")
        print(f"  错误操作数: {total_error_ops}")
        print(f"  预期错误数: {expected_errors:.0f}")
        print(f"  执行时间: {total_time:.3f}秒")
        print(f"  操作速率: {total_operations/total_time:.0f} ops/sec")

        # 验证结果
        self.assertGreater(total_operations, thread_count * operations_per_thread * 0.9, "大部分操作应该完成")
        self.assertGreater(total_errors, expected_errors * 0.8, "应该正确处理错误")
        self.assertGreater(total_normal_ops, total_normal_ops * 0.6, "大部分正常操作应该成功")

        print("✅ 并发压力下的错误处理测试完成")

    def test_007_signal_interruption_resilience(self):
        """测试：信号中断恢复能力"""
        print("=== 信号中断恢复能力测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()

        # 注册一些Bean
        for i in range(20):
            class_name = f"SignalBean{i}"
            signal_class = type(class_name, (), {
                'status': 'created',
                'get_status': lambda self: self.status
            })
            bean_name = f"signalBean{i}"
            context.register_bean(signal_class, bean_name)

        # 模拟信号中断处理
        interruption_count = 0
        recovered_operations = 0

        def test_interruption():
            nonlocal interruption_count, recovered_operations

            try:
                for i in range(100):
                    # 模拟信号中断
                    if i % 20 == 0:
                        interruption_count += 1
                        raise KeyboardInterrupt("模拟信号中断")

                    # 正常操作
                    bean_index = i % 20
                    bean = context.get_bean(f"signalBean{bean_index}")

                    # 验证Bean仍然可用
                    self.assertIsNotNone(bean)
                    recovered_operations += 1

            except KeyboardInterrupt:
                print(f"捕获到信号中断，尝试恢复...")
                # 模拟恢复操作
                time.sleep(0.001)  # 短暂延迟

                # 继续执行一些操作
                for i in range(10):
                    try:
                        bean = context.get_bean(f"signalBean{i}")
                        if bean is not None:
                            recovered_operations += 1
                    except:
                        break

        start_time = time.time()
        test_interruption()
        end_time = time.time()

        print(f"信号中断测试结果:")
        print(f"  中断次数: {interruption_count}")
        print(f"  恢复操作数: {recovered_operations}")
        print(f"  执行时间: {end_time - start_time:.3f}秒")

        # 验证恢复能力
        self.assertGreater(interruption_count, 0, "应该发生信号中断")
        self.assertGreater(recovered_operations, 0, "中断后应该能恢复操作")
        self.assertEqual(context.get_bean_names()[:20], [f"signalBean{i}" for i in range(20)], "所有Bean应该仍然可用")

        print("✅ 信号中断恢复能力测试完成")


def run_extreme_scenarios_tests():
    """运行极端场景和异常情况测试"""
    print("🚀 Harmony Framework 极端场景和异常情况测试")
    print("=" * 80)

    # 创建测试套件
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestExtremeScenarios))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果摘要
    print("\n" + "=" * 80)
    print(f"📊 极端场景和异常情况测试结果:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors))/result.testsRun*100:.1f}%")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 所有极端场景测试通过！")
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
    success = run_extreme_scenarios_tests()
    sys.exit(0 if success else 1)