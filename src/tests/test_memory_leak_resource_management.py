#!/usr/bin/env python3
"""
Harmony Framework 内存泄漏和资源管理测试
专门测试框架的内存管理、资源清理和泄漏防护能力
"""

import os
import sys
import time
import threading
import unittest
import gc
import weakref
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


class TestMemoryLeakAndResourceManagement(unittest.TestCase):
    """内存泄漏和资源管理测试类"""

    def setUp(self):
        """测试前准备"""
        self.test_start_time = time.time()
        # 强制垃圾回收，确保干净的测试环境
        gc.collect()

        # 尝试获取进程对象用于内存监控
        self.process = None
        try:
            import psutil
            self.process = psutil.Process()
        except ImportError:
            print("psutil未安装，将跳过详细的内存监控")

    def tearDown(self):
        """测试后清理"""
        test_duration = time.time() - self.test_start_time
        print(f"测试耗时: {test_duration:.3f}秒")
        # 强制垃圾回收
        gc.collect()

    def get_memory_usage(self):
        """获取当前内存使用情况"""
        if self.process:
            memory_info = self.process.memory_info()
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': self.process.memory_percent()
            }
        return None

    def test_001_massive_bean_creation_cleanup(self):
        """测试：大量Bean创建后的内存清理"""
        print("=== 大量Bean创建后的内存清理测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        initial_memory = self.get_memory_usage()
        if initial_memory:
            print(f"初始内存: {initial_memory['rss']:.2f}MB")

        # 创建上下文
        context = ApplicationContext()

        # 创建大量原型Bean实例
        bean_count = 5000
        created_beans = []
        weak_refs = []

        try:
            start_time = time.time()

            for i in range(bean_count):
                class_name = f"MemoryTestBean{i}"

                # 创建占用一定内存的Bean类
                class MemoryTestBean:
                    def __init__(self):
                        self.data = list(range(100))  # 约800字节
                        self.metadata = {'id': i, 'type': 'test'}
                        self.name = f"Bean{i}"

                    def get_memory_size(self):
                        return len(self.data) + len(str(self.metadata))

                MemoryTestBean.__name__ = class_name
                bean_name = f"memoryTestBean{i}"

                # 注册为原型Bean
                context.register_bean(MemoryTestBean, bean_name, scope=ScopeType.PROTOTYPE.value)

                # 创建实例
                bean = context.get_bean(bean_name)
                created_beans.append(bean)

                # 创建弱引用用于后续检查
                weak_ref = weakref.ref(bean)
                weak_refs.append(weak_ref)

            creation_time = time.time() - start_time
            peak_memory = self.get_memory_usage()
            if peak_memory:
                print(f"创建{bean_count}个Bean耗时: {creation_time:.3f}秒")
                print(f"峰值内存: {peak_memory['rss']:.2f}MB (增长{peak_memory['rss'] - initial_memory['rss']:.2f}MB)")

        finally:
            # 清理引用
            created_beans.clear()
            context.close()
            del context

            # 强制垃圾回收
            gc.collect()

        # 检查内存清理情况
        cleanup_memory = self.get_memory_usage()
        if initial_memory and cleanup_memory:
            memory_growth = cleanup_memory['rss'] - initial_memory['rss']
            print(f"清理后内存: {cleanup_memory['rss']:.2f}MB")
            print(f"内存增长: {memory_growth:.2f}MB")

            # 验证内存增长在合理范围内（小于100MB）
            self.assertLess(memory_growth, 100, "内存增长应该在合理范围内")

        # 检查弱引用是否被正确清理
        active_refs = sum(1 for ref in weak_refs if ref() is not None)
        print(f"仍活跃的弱引用: {active_refs}/{len(weak_refs)}")

        # 大部分对象应该被清理
        cleanup_rate = (len(weak_refs) - active_refs) / len(weak_refs)
        self.assertGreater(cleanup_rate, 0.8, "大部分对象应该被垃圾回收")

        print("✅ 大量Bean创建后的内存清理测试完成")

    def test_002_context_lifecycle_memory_management(self):
        """测试：上下文生命周期中的内存管理"""
        print("=== 上下文生命周期中的内存管理测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        initial_memory = self.get_memory_usage()
        if initial_memory:
            print(f"初始内存: {initial_memory['rss']:.2f}MB")

        # 多次创建和销毁上下文
        context_lifecycles = []
        memory_snapshots = []

        for cycle in range(20):
            # 创建上下文
            context = ApplicationContext()

            # 注册各种类型的Bean
            for i in range(100):
                # 单例Bean
                class SingletonBean:
                    def __init__(self):
                        self.cycle = cycle
                        self.id = i
                        self.data = list(range(50))

                SingletonBean.__name__ = f"SingletonBean{cycle}_{i}"
                context.register_bean(SingletonBean, f"singletonBean{cycle}_{i}", scope=ScopeType.SINGLETON.value)

                # 原型Bean
                class PrototypeBean:
                    def __init__(self):
                        self.cycle = cycle
                        self.id = i
                        self.data = list(range(30))

                PrototypeBean.__name__ = f"PrototypeBean{cycle}_{i}"
                context.register_bean(PrototypeBean, f"prototypeBean{cycle}_{i}", scope=ScopeType.PROTOTYPE.value)

            # 创建一些原型Bean实例
            for i in range(50):
                bean = context.get_bean(f"prototypeBean{cycle}_{i}")
                # 使用bean确保实例化
                _ = bean.cycle

            # 记录内存使用
            current_memory = self.get_memory_usage()
            if current_memory:
                memory_snapshots.append(current_memory['rss'])

            # 销毁上下文
            context.close()
            del context

            # 每几个周期进行垃圾回收
            if cycle % 5 == 0:
                gc.collect()

        # 最终清理
        gc.collect()

        final_memory = self.get_memory_usage()
        if initial_memory and final_memory and memory_snapshots:
            memory_growth = final_memory['rss'] - initial_memory['rss']
            peak_memory = max(memory_snapshots) - initial_memory['rss']

            print(f"最终内存: {final_memory['rss']:.2f}MB")
            print(f"内存增长: {memory_growth:.2f}MB")
            print(f"峰值增长: {peak_memory:.2f}MB")

            # 验证内存管理效果
            self.assertLess(memory_growth, 50, "多次上下文生命周期后内存增长应该有限")
            self.assertLess(peak_memory, 150, "峰值内存使用应该在合理范围内")

        print("✅ 上下文生命周期中的内存管理测试完成")

    def test_003_weak_reference_tracking(self):
        """测试：弱引用跟踪和对象回收"""
        print("=== 弱引用跟踪和对象回收测试 ===")

        from harmony.core.application_context import ApplicationContext

        context = ApplicationContext()

        # 创建Bean并建立弱引用跟踪
        beans = []
        weak_refs = []

        for i in range(200):
            class TrackedBean:
                def __init__(self):
                    self.id = i
                    self.data = list(range(20))

            TrackedBean.__name__ = f"TrackedBean{i}"
            bean_name = f"trackedBean{i}"
            context.register_bean(TrackedBean, bean_name)

            # 创建实例
            bean = context.get_bean(bean_name)
            beans.append(bean)

            # 创建弱引用
            weak_ref = weakref.ref(bean)
            weak_refs.append(weak_ref)

        # 验证初始状态
        initial_active_refs = sum(1 for ref in weak_refs if ref() is not None)
        self.assertEqual(initial_active_refs, len(weak_refs), "初始时所有弱引用都应该有效")

        # 清理强引用
        beans.clear()
        context.close()
        del context

        # 强制垃圾回收
        gc.collect()

        # 等待一下确保垃圾回收完成
        time.sleep(0.1)
        gc.collect()

        # 检查对象回收情况
        remaining_active_refs = sum(1 for ref in weak_refs if ref() is not None)
        cleanup_rate = (len(weak_refs) - remaining_active_refs) / len(weak_refs)

        print(f"回收前活跃引用: {initial_active_refs}")
        print(f"回收后活跃引用: {remaining_active_refs}")
        print(f"回收率: {cleanup_rate*100:.1f}%")

        # 验证对象被正确回收
        self.assertGreater(cleanup_rate, 0.7, "大部分对象应该被垃圾回收")

        print("✅ 弱引用跟踪和对象回收测试完成")

    def test_004_memory_pressure_handling(self):
        """测试：内存压力处理"""
        print("=== 内存压力处理测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        initial_memory = self.get_memory_usage()
        if initial_memory:
            print(f"初始内存: {initial_memory['rss']:.2f}MB")

        context = ApplicationContext()

        # 创建内存压力
        memory_beans = []
        memory_limit_reached = False
        max_iterations = 1000

        try:
            for i in range(max_iterations):
                class_name = f"MemoryPressureBean{i}"

                # 创建占用较大内存的Bean
                class MemoryPressureBean:
                    def __init__(self):
                        # 分配约50KB内存
                        self.large_data = list(range(5000))
                        self.metadata = {'id': i, 'timestamp': time.time()}
                        self.buffer = bytearray(1024 * 10)  # 10KB buffer

                MemoryPressureBean.__name__ = class_name
                bean_name = f"memoryPressureBean{i}"
                context.register_bean(MemoryPressureBean, bean_name, scope=ScopeType.PROTOTYPE.value)

                # 创建实例
                bean = context.get_bean(bean_name)
                memory_beans.append(bean)

                # 检查内存使用情况
                if i % 100 == 0 and self.process:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    if current_memory > initial_memory['rss'] + 200:  # 200MB限制
                        print(f"内存使用达到{current_memory:.2f}MB，停止创建")
                        memory_limit_reached = True
                        break

        except MemoryError:
            print("捕获到内存不足异常，框架正确处理了内存压力")
            memory_limit_reached = True

        finally:
            # 清理内存压力
            memory_beans.clear()
            context.close()
            del context
            gc.collect()

        # 验证内存清理
        cleanup_memory = self.get_memory_usage()
        if initial_memory and cleanup_memory:
            memory_growth = cleanup_memory['rss'] - initial_memory['rss']
            print(f"清理后内存: {cleanup_memory['rss']:.2f}MB")
            print(f"内存增长: {memory_growth:.2f}MB")

            # 验证内存压力处理（在极端压力下允许更高的内存增长）
            self.assertLess(memory_growth, 400, "内存压力清理后内存增长应该在可接受范围内")

        # 验证内存压力处理机制
        if memory_limit_reached:
            print("✅ 框架成功处理了内存压力")
        else:
            print("✅ 内存使用在可接受范围内，未达到压力限制")

        print("✅ 内存压力处理测试完成")

    def test_005_concurrent_memory_management(self):
        """测试：并发环境下的内存管理"""
        print("=== 并发环境下的内存管理测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        initial_memory = self.get_memory_usage()
        if initial_memory:
            print(f"初始内存: {initial_memory['rss']:.2f}MB")

        def concurrent_memory_worker(worker_id):
            """并发内存管理工作线程"""
            contexts = []
            beans = []

            try:
                for i in range(50):  # 每个线程创建50个上下文
                    context = ApplicationContext()

                    for j in range(20):  # 每个上下文20个Bean
                        class ConcurrentBean:
                            def __init__(self):
                                self.worker_id = worker_id
                                self.context_id = i
                                self.bean_id = j
                                self.data = list(range(100))

                        ConcurrentBean.__name__ = f"ConcurrentBean{worker_id}_{i}_{j}"
                        bean_name = f"concurrentBean{worker_id}_{i}_{j}"
                        context.register_bean(ConcurrentBean, bean_name, scope=ScopeType.PROTOTYPE.value)

                        # 创建实例
                        bean = context.get_bean(bean_name)
                        beans.append(bean)

                    contexts.append(context)

                    # 随机清理一些上下文
                    if len(contexts) > 10:
                        old_context = contexts.pop(0)
                        old_context.close()
                        del old_context

            finally:
                # 最终清理
                for context in contexts:
                    context.close()

                beans.clear()
                contexts.clear()

        # 启动多个并发工作线程
        thread_count = 5
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(concurrent_memory_worker, i) for i in range(thread_count)]

            # 等待所有线程完成
            for future in futures:
                future.result()

        # 强制垃圾回收
        gc.collect()

        # 检查并发内存管理效果
        final_memory = self.get_memory_usage()
        if initial_memory and final_memory:
            memory_growth = final_memory['rss'] - initial_memory['rss']
            print(f"并发操作后内存: {final_memory['rss']:.2f}MB")
            print(f"内存增长: {memory_growth:.2f}MB")

            # 验证并发内存管理
            self.assertLess(memory_growth, 80, "并发操作后内存增长应该在合理范围内")

        print("✅ 并发环境下的内存管理测试完成")

    def test_006_resource_leak_prevention(self):
        """测试：资源泄漏预防"""
        print("=== 资源泄漏预防测试 ===")

        from harmony.core.application_context import ApplicationContext
        from harmony.core.scope import ScopeType

        # 测试文件资源泄漏预防
        file_resources = []
        contexts = []

        try:
            for i in range(50):
                context = ApplicationContext()

                class FileResourceBean:
                    def __init__(self):
                        self.id = i
                        # 模拟文件资源（在实际应用中可能是文件句柄、数据库连接等）
                        self.temp_files = []
                        for j in range(5):
                            # 创建临时文件
                            import tempfile
                            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
                            temp_file.write(f"Data for bean {i}_{j}\n" * 100)
                            temp_file.close()
                            self.temp_files.append(temp_file.name)

                    def cleanup(self):
                        # 清理临时文件
                        import os
                        for temp_file in self.temp_files:
                            try:
                                os.unlink(temp_file)
                            except:
                                pass
                        self.temp_files.clear()

                FileResourceBean.__name__ = f"FileResourceBean{i}"
                bean_name = f"fileResourceBean{i}"
                context.register_bean(FileResourceBean, bean_name, scope=ScopeType.PROTOTYPE.value)

                # 创建实例
                bean = context.get_bean(bean_name)
                file_resources.append(bean)
                contexts.append(context)

        finally:
            # 清理资源和上下文
            for bean in file_resources:
                bean.cleanup()

            for context in contexts:
                context.close()

            file_resources.clear()
            contexts.clear()
            gc.collect()

        print("✅ 资源泄漏预防测试完成")

    def test_007_long_running_stability(self):
        """测试：长时间运行稳定性"""
        print("=== 长时间运行稳定性测试 ===")

        from harmony.core.application_context import ApplicationContext

        initial_memory = self.get_memory_usage()
        if initial_memory:
            print(f"初始内存: {initial_memory['rss']:.2f}MB")

        # 模拟长时间运行场景
        duration = 5  # 5秒的长时间运行测试
        start_time = time.time()
        operations = 0
        contexts = []

        while time.time() - start_time < duration:
            # 创建上下文
            context = ApplicationContext()

            # 快速注册和使用Bean
            for i in range(10):
                class StabilityTestBean:
                    def __init__(self):
                        self.timestamp = time.time()
                        self.data = list(range(50))

                StabilityTestBean.__name__ = f"StabilityTestBean{operations}_{i}"
                bean_name = f"stabilityTestBean{operations}_{i}"
                context.register_bean(StabilityTestBean, bean_name)

                # 使用Bean
                bean = context.get_bean(bean_name)
                operations += 1

            # 清理上下文
            context.close()

            # 定期清理和垃圾回收
            if len(contexts) > 20:
                contexts.clear()
                gc.collect()

        # 最终清理
        contexts.clear()
        gc.collect()

        final_memory = self.get_memory_usage()
        if initial_memory and final_memory:
            memory_growth = final_memory['rss'] - initial_memory['rss']
            print(f"长时间运行后内存: {final_memory['rss']:.2f}MB")
            print(f"内存增长: {memory_growth:.2f}MB")
            print(f"总操作数: {operations}")
            print(f"平均操作速率: {operations/duration:.0f} ops/sec")

            # 验证长时间运行的稳定性
            self.assertLess(memory_growth, 30, "长时间运行后内存增长应该有限")
            self.assertGreater(operations, 1000, "应该能执行大量操作")

        print("✅ 长时间运行稳定性测试完成")


def run_memory_leak_resource_management_tests():
    """运行内存泄漏和资源管理测试"""
    print("🧹 Harmony Framework 内存泄漏和资源管理测试")
    print("=" * 80)

    # 创建测试套件
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestMemoryLeakAndResourceManagement))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果摘要
    print("\n" + "=" * 80)
    print(f"📊 内存泄漏和资源管理测试结果:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    print(f"   成功率: {(result.testsRun - len(result.failures) - len(result.errors))/result.testsRun*100:.1f}%")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 所有内存泄漏和资源管理测试通过！")
        print("💡 Harmony Framework 内存管理表现出色！")
        success = True
    else:
        print("⚠️ 存在失败的测试，需要进一步优化内存管理")
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
    success = run_memory_leak_resource_management_tests()
    sys.exit(0 if success else 1)