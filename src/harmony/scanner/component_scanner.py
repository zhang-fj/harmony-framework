"""增强的组件扫描器 - 高性能并发扫描"""

import concurrent.futures
import importlib
import inspect
import os
import threading
from pathlib import Path
from typing import List, Type, Set, Dict, Any

from ..annotations.component import create_bean_definition
from ..config.environment import environment_manager
from ..core.bean_definition import BeanDefinition
from ..extensions.cache import scan_cache, metadata_cache
from ..extensions.reflection_cache import reflection_cache
from ..utils.logger import get_logger


class ComponentScanner:
    """组件扫描器 - 支持自动发现和注册Bean"""

    def __init__(self):
        self.scanned_packages: Set[str] = set()
        self.scanned_classes: Set[Type] = set()
        self.component_filters: List[callable] = []
        self.exclude_patterns: List[str] = []
        self.include_patterns: List[str] = []
        self._scan_lock = threading.RLock()
        self._max_workers = min(32, (os.cpu_count() or 1) + 4)  # 并发扫描线程数
        self.logger = get_logger('component_scanner')

    def scan_packages(self, *packages: str) -> List[BeanDefinition]:
        """
        扫描指定的包，自动发现并注册组件

        Args:
            *packages: 要扫描的包名列表

        Returns:
            发现的Bean定义列表
        """
        bean_definitions = []

        for package in packages:
            if package in self.scanned_packages:
                continue

            self.scanned_packages.add(package)
            definitions = self._scan_package(package)
            bean_definitions.extend(definitions)

        return bean_definitions

    def _scan_package(self, package_name: str) -> List[BeanDefinition]:
        """扫描单个包 - 使用缓存优化"""
        try:
            package = importlib.import_module(package_name)
            # 检查包是否有__file__属性
            if hasattr(package, '__file__') and package.__file__:
                package_path = Path(package.__file__).parent
            else:
                # 对于没有__file__属性的包（如内置包），跳过扫描
                self.logger.warning(f"Skipping package {package_name}: no file path available")
                return []

            # 尝试从缓存获取扫描结果
            cached_result = scan_cache.get(package_name, package_path)
            if cached_result is not None:
                # 更新已扫描类集合
                for definition in cached_result:
                    self.scanned_classes.add(definition.bean_type)
                return cached_result

            # 缓存未命中，执行实际扫描
            bean_definitions = []
            modules_to_scan = []

            # 先收集所有需要扫描的模块
            for root, dirs, files in os.walk(package_path):
                # 跳过__pycache__目录
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')

                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        module_path = os.path.join(root, file)
                        module_name = self._get_module_name(module_path, package_path, package_name)
                        modules_to_scan.append(module_name)

            # 批量扫描模块
            for module_name in modules_to_scan:
                try:
                    definitions = self._scan_module(module_name)
                    bean_definitions.extend(definitions)
                except Exception as e:
                    # 忽略无法导入的模块
                    continue

            # 缓存扫描结果
            if bean_definitions:
                scan_cache.put(package_name, package_path, bean_definitions)

            return bean_definitions

        except ImportError:
            # 包不存在时跳过
            return []

    def _scan_module(self, module_name: str) -> List[BeanDefinition]:
        """扫描单个模块"""
        bean_definitions = []

        try:
            module = importlib.import_module(module_name)

            # 检查模块中的所有类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 跳过导入的类（不在当前模块中定义的类）
                if obj.__module__ != module_name:
                    continue

                # 跳过已经扫描过的类
                if obj in self.scanned_classes:
                    continue

                self.scanned_classes.add(obj)

                # 检查是否为组件类
                if self._is_component_class(obj):
                    definition = create_bean_definition(obj)

                    # 应用过滤器
                    if self._apply_filters(obj, definition):
                        bean_definitions.append(definition)

        except ImportError:
            # 模块无法导入时跳过
            pass

        return bean_definitions

    def _is_component_class(self, cls: Type) -> bool:
        """检查类是否为组件类"""
        # 检查各种组件注解
        has_annotations = (
                hasattr(cls, '__harmony_component__') or
                hasattr(cls, '__harmony_bean__') or
                hasattr(cls, '__harmony_service__') or
                hasattr(cls, '__harmony_repository__') or
                hasattr(cls, '__harmony_controller__')
        )

        if not has_annotations:
            return False

        # 检查是否应该包含
        if self.include_patterns:
            class_name = cls.__name__
            if not any(pattern in class_name for pattern in self.include_patterns):
                return False

        # 检查是否应该排除
        if self.exclude_patterns:
            class_name = cls.__name__
            if any(pattern in class_name for pattern in self.exclude_patterns):
                return False

        return True

    def _apply_filters(self, cls: Type, definition: BeanDefinition) -> bool:
        """应用自定义过滤器"""
        for filter_func in self.component_filters:
            if not filter_func(cls, definition):
                return False
        return True

    def _get_module_name(self, file_path: str, package_path: Path, package_name: str) -> str:
        """根据文件路径获取模块名"""
        relative_path = Path(file_path).relative_to(package_path)
        module_path = relative_path.with_suffix('')
        module_parts = [package_name] + list(module_path.parts)
        return '.'.join(module_parts)

    def add_include_pattern(self, pattern: str):
        """添加包含模式"""
        self.include_patterns.append(pattern)

    def add_exclude_pattern(self, pattern: str):
        """添加排除模式"""
        self.exclude_patterns.append(pattern)

    def add_filter(self, filter_func: callable):
        """添加自定义过滤器"""
        self.component_filters.append(filter_func)

    def scan_classes(self, *classes: Type) -> List[BeanDefinition]:
        """
        直接扫描指定的类

        Args:
            *classes: 要扫描的类列表

        Returns:
            发现的Bean定义列表
        """
        bean_definitions = []

        for cls in classes:
            if cls in self.scanned_classes:
                continue

            self.scanned_classes.add(cls)

            if self._is_component_class(cls):
                definition = create_bean_definition(cls)
                if self._apply_filters(cls, definition):
                    bean_definitions.append(definition)

        return bean_definitions

    def scan_profile_specific(self, base_packages: List[str]) -> List[BeanDefinition]:
        """
        基于当前活跃的profile扫描组件

        Args:
            base_packages: 基础包列表

        Returns:
            适合当前profile的Bean定义列表
        """
        active_profiles = environment_manager.get_active_profiles()

        # 如果没有特定的profile，扫描所有组件
        if not active_profiles or 'default' in active_profiles:
            return self.scan_packages(*base_packages)

        # 添加profile过滤器
        def profile_filter(cls: Type, definition: BeanDefinition) -> bool:
            # 检查类是否有profile特定注解
            if hasattr(cls, '__harmony_profiles__'):
                required_profiles = getattr(cls, '__harmony_profiles__')
                return any(profile in active_profiles for profile in required_profiles)
            return True  # 默认包含所有非profile特定的组件

        # 临时添加过滤器
        self.add_filter(profile_filter)

        try:
            bean_definitions = self.scan_packages(*base_packages)
        finally:
            # 移除临时过滤器
            if profile_filter in self.component_filters:
                self.component_filters.remove(profile_filter)

        return bean_definitions

    def get_scanned_count(self) -> Dict[str, int]:
        """获取扫描统计信息"""
        cache_stats = scan_cache.get_stats()
        return {
            'scanned_packages': len(self.scanned_packages),
            'scanned_classes': len(self.scanned_classes),
            'exclude_patterns': len(self.exclude_patterns),
            'include_patterns': len(self.include_patterns),
            'custom_filters': len(self.component_filters),
            'cache_hit_rate': cache_stats.get('hit_rate', 0),
            'cache_size': cache_stats.get('cache_size', 0)
        }

    def clear_cache(self):
        """清空扫描缓存"""
        scan_cache.clear()
        metadata_cache.clear()

    def reset(self):
        """重置扫描器状态"""
        self.scanned_packages.clear()
        self.scanned_classes.clear()
        self.component_filters.clear()
        self.exclude_patterns.clear()
        self.include_patterns.clear()

    def scan_packages_concurrent(self, *packages: str) -> List[BeanDefinition]:
        """
        并发扫描指定的包 - 使用ClassPathScanningComponentScanner实现

        Args:
            *packages: 要扫描的包名列表

        Returns:
            发现的Bean定义列表
        """
        # 如果还没有并发扫描能力，回退到顺序扫描
        if hasattr(self, '_max_workers') and self._max_workers > 1:
            return self._scan_packages_concurrent_impl(*packages)
        else:
            return self.scan_packages(*packages)

    def _scan_packages_concurrent_impl(self, *packages: str) -> List[BeanDefinition]:
        """并发扫描实现（优化版）"""
        with self._scan_lock:
            bean_definitions = []
            new_packages = [pkg for pkg in packages if pkg not in self.scanned_packages]

            if not new_packages:
                return bean_definitions

            # 立即标记为已扫描，避免重复扫描
            for package in new_packages:
                self.scanned_packages.add(package)

        # 并发扫描（在锁外执行）
        max_workers = min(self._max_workers, len(new_packages))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交扫描任务
            future_to_package = {
                executor.submit(self._scan_package_safe, package): package
                for package in new_packages
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_package):
                package = future_to_package[future]
                try:
                    definitions = future.result(timeout=30)
                    bean_definitions.extend(definitions)
                except Exception as e:
                    # 记录错误但继续扫描其他包
                    continue

        return bean_definitions

    def _scan_package_safe(self, package: str) -> List[BeanDefinition]:
        """安全的包扫描（异常处理优化）"""
        try:
            return self._scan_package(package)
        except Exception as e:
            # 静默处理扫描错误，避免影响其他包的扫描
            return []

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取扫描性能统计"""
        cache_stats = scan_cache.get_stats()

        return {
            'scanned_packages': len(self.scanned_packages),
            'scanned_classes': len(self.scanned_classes),
            'cache_stats': cache_stats,
            'concurrent_enabled': hasattr(self, '_max_workers') and self._max_workers > 1
        }


class ClassPathScanningComponentScanner(ComponentScanner):
    """类路径扫描组件扫描器 - 支持更高级的扫描功能"""

    def __init__(self, base_packages: List[str] = None):
        super().__init__()
        self.base_packages = base_packages or []
        self.classpath_entries: List[str] = []

    def scan_base_packages(self) -> List[BeanDefinition]:
        """扫描基础包"""
        return self.scan_packages(*self.base_packages)

    def find_candidate_components(self, base_package: str) -> List[Type]:
        """查找候选组件类"""
        candidates = []

        try:
            package = importlib.import_module(base_package)
            package_path = Path(package.__file__).parent

            for root, dirs, files in os.walk(package_path):
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')

                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        module_path = os.path.join(root, file)
                        module_name = self._get_module_name(module_path, package_path, base_package)

                        try:
                            module = importlib.import_module(module_name)

                            for name, obj in inspect.getmembers(module, inspect.isclass):
                                if obj.__module__ == module_name and self._is_component_class(obj):
                                    candidates.append(obj)

                        except ImportError:
                            pass

        except ImportError:
            pass

        return candidates

    def set_base_packages(self, *packages: str):
        """设置基础包"""
        self.base_packages = list(packages)

    def add_classpath_entry(self, entry: str):
        """添加类路径条目"""
        if entry not in self.classpath_entries:
            self.classpath_entries.append(entry)

    def scan_packages_concurrent(self, *packages: str) -> List[BeanDefinition]:
        """
        并发扫描指定的包 - 高性能版本

        Args:
            *packages: 要扫描的包名列表

        Returns:
            发现的Bean定义列表
        """
        with self._scan_lock:
            bean_definitions = []
            new_packages = [pkg for pkg in packages if pkg not in self.scanned_packages]

            if not new_packages:
                return bean_definitions

            # 标记为已扫描
            for package in new_packages:
                self.scanned_packages.add(package)

            # 使用线程池并发扫描
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # 提交扫描任务
                future_to_package = {
                    executor.submit(self._scan_package_cached, package): package
                    for package in new_packages
                }

                # 收集结果
                for future in concurrent.futures.as_completed(future_to_package):
                    try:
                        definitions = future.result(timeout=30)  # 30秒超时
                        bean_definitions.extend(definitions)
                    except Exception as e:
                        package = future_to_package[future]
                        # 记录错误但继续扫描其他包
                        continue

            return bean_definitions

    def _scan_package_cached(self, package_name: str) -> List[BeanDefinition]:
        """带缓存的包扫描（线程安全版本）"""
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent

            # 尝试从缓存获取扫描结果
            cached_result = scan_cache.get(package_name, package_path)
            if cached_result is not None:
                # 更新已扫描类集合（线程安全）
                with self._scan_lock:
                    for definition in cached_result:
                        self.scanned_classes.add(definition.bean_type)
                return cached_result

            # 缓存未命中，执行并发模块扫描
            modules_to_scan = self._collect_modules_to_scan(package_path, package_name)

            if len(modules_to_scan) <= 2:
                # 模块数量少时，使用顺序扫描
                return self._scan_modules_sequential(modules_to_scan, package_name, package_path)
            else:
                # 模块数量多时，使用并发扫描
                return self._scan_modules_concurrent(modules_to_scan, package_name, package_path)

        except ImportError:
            return []

    def _collect_modules_to_scan(self, package_path: Path, package_name: str) -> List[str]:
        """收集需要扫描的模块列表"""
        modules_to_scan = []

        for root, dirs, files in os.walk(package_path):
            # 跳过__pycache__目录
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    module_path = os.path.join(root, file)
                    module_name = self._get_module_name(module_path, package_path, package_name)
                    modules_to_scan.append(module_name)

        return modules_to_scan

    def _scan_modules_sequential(self, modules_to_scan: List[str],
                                 package_name: str, package_path: Path) -> List[BeanDefinition]:
        """顺序扫描模块"""
        bean_definitions = []

        for module_name in modules_to_scan:
            try:
                definitions = self._scan_module_optimized(module_name)
                bean_definitions.extend(definitions)
            except Exception:
                # 忽略无法导入的模块
                continue

        # 缓存扫描结果
        if bean_definitions:
            scan_cache.put(package_name, package_path, bean_definitions)

        return bean_definitions

    def _scan_modules_concurrent(self, modules_to_scan: List[str],
                                 package_name: str, package_path: Path) -> List[BeanDefinition]:
        """并发扫描模块"""
        all_definitions = []

        # 使用较小的线程池避免资源过度使用
        max_workers = min(self._max_workers, len(modules_to_scan))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交模块扫描任务
            future_to_module = {
                executor.submit(self._scan_module_optimized, module_name): module_name
                for module_name in modules_to_scan
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_module):
                try:
                    definitions = future.result(timeout=10)  # 10秒超时
                    all_definitions.extend(definitions)
                except Exception:
                    # 忽略无法扫描的模块
                    continue

        # 缓存扫描结果
        if all_definitions:
            scan_cache.put(package_name, package_path, all_definitions)

        return all_definitions

    def _scan_module_optimized(self, module_name: str) -> List[BeanDefinition]:
        """优化的模块扫描（使用反射缓存）"""
        bean_definitions = []

        try:
            module = importlib.import_module(module_name)

            # 使用反射缓存优化类成员检查
            annotations = reflection_cache.get_annotations(module)

            # 检查模块中的所有类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 跳过导入的类（不在当前模块中定义的类）
                if obj.__module__ != module_name:
                    continue

                # 线程安全地检查是否已扫描
                with self._scan_lock:
                    if obj in self.scanned_classes:
                        continue
                    self.scanned_classes.add(obj)

                # 检查是否为组件类（使用缓存）
                if self._is_component_class_cached(obj):
                    definition = create_bean_definition(obj)

                    # 应用过滤器
                    if self._apply_filters(obj, definition):
                        bean_definitions.append(definition)

        except ImportError:
            # 模块无法导入时跳过
            pass

        return bean_definitions

    def _is_component_class_cached(self, cls: Type) -> bool:
        """使用缓存检查类是否为组件类"""
        # 使用反射缓存获取类注解
        annotations = reflection_cache.get_annotations(cls)

        # 检查各种组件注解
        has_annotations = any(
            annotation_key in annotations
            for annotation_key in [
                '__harmony_component__', '__harmony_bean__',
                '__harmony_service__', '__harmony_repository__', '__harmony_controller__'
            ]
        )

        if not has_annotations:
            return False

        # 检查包含/排除模式
        class_name = cls.__name__

        if self.include_patterns:
            if not any(pattern in class_name for pattern in self.include_patterns):
                return False

        if self.exclude_patterns:
            if any(pattern in class_name for pattern in self.exclude_patterns):
                return False

        return True

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取扫描性能统计"""
        cache_stats = scan_cache.get_stats()
        reflection_stats = reflection_cache.get_cache_stats()

        return {
            'scanned_packages': len(self.scanned_packages),
            'scanned_classes': len(self.scanned_classes),
            'max_workers': self._max_workers,
            'cache_stats': cache_stats,
            'reflection_cache_stats': reflection_stats,
            'concurrent_enabled': self._max_workers > 1
        }
