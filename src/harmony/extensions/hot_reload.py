"""
配置热重载机制 - 支持配置文件变化时自动重新加载
"""

import hashlib
import importlib
import importlib.util
import json
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Set


@dataclass
class ConfigChange:
    """配置变更信息"""
    key: str
    old_value: Any
    new_value: Any
    change_type: str  # 'added', 'modified', 'deleted'
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class ConfigChangeHandler(ABC):
    """配置变更处理器抽象基类"""

    @abstractmethod
    def handle_config_change(self, change: ConfigChange) -> None:
        """处理配置变更"""
        pass

    @abstractmethod
    def get_supported_keys(self) -> List[str]:
        """获取支持的配置键"""
        pass


class ConfigurationWatcher:
    """配置文件监控器"""

    def __init__(self, watch_paths: List[str], check_interval: float = 1.0):
        self.watch_paths = [Path(p) for p in watch_paths]
        self.check_interval = check_interval
        self._file_hashes: Dict[Path, str] = {}
        self._last_modified: Dict[Path, float] = {}
        self._change_handlers: List[Callable[[ConfigChange], None]] = []
        self._watch_active = False
        self._watch_thread = None
        self._lock = threading.RLock()

        # 初始化文件状态
        self._initialize_file_states()

    def _initialize_file_states(self):
        """初始化文件状态"""
        with self._lock:
            for path in self.watch_paths:
                if path.exists() and path.is_file():
                    self._file_hashes[path] = self._calculate_file_hash(path)
                    self._last_modified[path] = path.stat().st_mtime

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def add_change_handler(self, handler: Callable[[ConfigChange], None]):
        """添加配置变更处理器"""
        with self._lock:
            self._change_handlers.append(handler)

    def remove_change_handler(self, handler: Callable[[ConfigChange], None]) -> bool:
        """移除配置变更处理器"""
        with self._lock:
            if handler in self._change_handlers:
                self._change_handlers.remove(handler)
                return True
            return False

    def start_watching(self):
        """开始监控文件变化"""
        if self._watch_active:
            return

        self._watch_active = True
        self._watch_thread = threading.Thread(target=self._watch_files, daemon=True)
        self._watch_thread.start()

    def stop_watching(self):
        """停止监控文件变化"""
        self._watch_active = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5.0)

    def _watch_files(self):
        """监控文件变化的线程函数"""
        while self._watch_active:
            try:
                self._check_file_changes()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"File watching error: {e}")

    def _check_file_changes(self):
        """检查文件变化"""
        with self._lock:
            for path in self.watch_paths:
                if path.exists():
                    current_hash = self._calculate_file_hash(path)
                    current_mtime = path.stat().st_mtime

                    if path not in self._file_hashes:
                        # 新文件
                        self._file_hashes[path] = current_hash
                        self._last_modified[path] = current_mtime
                        self._notify_file_added(path)

                    elif current_hash != self._file_hashes[path]:
                        # 文件内容变化
                        old_hash = self._file_hashes[path]
                        self._file_hashes[path] = current_hash
                        self._last_modified[path] = current_mtime
                        self._notify_file_changed(path, old_hash, current_hash)

                elif path in self._file_hashes:
                    # 文件被删除
                    self._notify_file_deleted(path)
                    del self._file_hashes[path]
                    del self._last_modified[path]

    def _notify_file_added(self, file_path: Path):
        """通知文件添加"""
        change = ConfigChange(
            key=str(file_path),
            old_value=None,
            new_value="FILE_ADDED",
            change_type="added",
            source="file_watcher"
        )
        self._notify_handlers(change)

    def _notify_file_changed(self, file_path: Path, old_hash: str, new_hash: str):
        """通知文件变化"""
        change = ConfigChange(
            key=str(file_path),
            old_value=old_hash,
            new_value=new_hash,
            change_type="modified",
            source="file_watcher"
        )
        self._notify_handlers(change)

    def _notify_file_deleted(self, file_path: Path):
        """通知文件删除"""
        change = ConfigChange(
            key=str(file_path),
            old_value="FILE_EXISTED",
            new_value=None,
            change_type="deleted",
            source="file_watcher"
        )
        self._notify_handlers(change)

    def _notify_handlers(self, change: ConfigChange):
        """通知所有处理器"""
        for handler in self._change_handlers:
            try:
                handler(change)
            except Exception as e:
                print(f"Config change handler error: {e}")


class ConfigurationReloader:
    """配置重新加载器"""

    def __init__(self, config_sources: List[str], reload_callback: Optional[Callable[[], None]] = None):
        self.config_sources = [Path(source) for source in config_sources]
        self.reload_callback = reload_callback
        self.watcher = ConfigurationWatcher([str(s) for s in config_sources], check_interval=0.5)
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._change_handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

        # 注册文件变更处理器
        self.watcher.add_change_handler(self._handle_file_change)

    def _handle_file_change(self, change: ConfigChange):
        """处理文件变更"""
        with self._lock:
            try:
                file_path = Path(change.key)

                if change.change_type == "modified":
                    # 重新加载配置文件
                    self._reload_config_file(file_path)

                    # 调用全局回调
                    if self.reload_callback:
                        self.reload_callback()

                    # 通知特定处理器
                    self._notify_config_handlers(file_path)

            except Exception as e:
                print(f"Config reload error: {e}")

    def _reload_config_file(self, file_path: Path):
        """重新加载配置文件"""
        try:
            config_data = self._load_config_file(file_path)
            self._config_cache[str(file_path)] = config_data
        except Exception as e:
            print(f"Failed to reload config file {file_path}: {e}")

    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        config_data = {}

        if not file_path.exists():
            return config_data

        try:
            if file_path.suffix.lower() in ['.json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif file_path.suffix.lower() in ['.py']:
                # 动态导入Python配置文件
                self._reload_python_config(file_path)
            else:
                # 尝试解析键值对格式
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                config_data[key.strip()] = value.strip().strip('"\'')
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")

        return config_data

    def _reload_python_config(self, file_path: Path):
        """重新加载Python配置文件"""
        try:
            # 构建模块名称
            module_name = file_path.stem
            if file_path.parent.name:
                module_name = f"{file_path.parent.name}.{module_name}"

            # 如果模块已存在，重新加载
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    sys.modules[module_name] = module

        except Exception as e:
            print(f"Error reloading Python config {file_path}: {e}")

    def register_handler(self, file_pattern: str, handler: Callable[[ConfigChange], None]):
        """注册配置变更处理器"""
        with self._lock:
            if file_pattern not in self._change_handlers:
                self._change_handlers[file_pattern] = []
            self._change_handlers[file_pattern].append(handler)

    def unregister_handler(self, file_pattern: str, handler: Callable[[ConfigChange], None]) -> bool:
        """取消注册配置变更处理器"""
        with self._lock:
            if file_pattern in self._change_handlers:
                if handler in self._change_handlers[file_pattern]:
                    self._change_handlers[file_pattern].remove(handler)
                    return True
            return False

    def _notify_config_handlers(self, file_path: Path):
        """通知配置处理器"""
        file_str = str(file_path)

        for pattern, handlers in self._change_handlers.items():
            if pattern in file_str or file_str.endswith(pattern):
                for handler in handlers:
                    try:
                        change = ConfigChange(
                            key=file_str,
                            old_value=None,
                            new_value=self._config_cache.get(file_str, {}),
                            change_type="reloaded",
                            source="config_reloader"
                        )
                        handler(change)
                    except Exception as e:
                        print(f"Config handler error: {e}")

    def start_watching(self):
        """开始监控配置变化"""
        # 初始加载所有配置
        for config_path in self.config_sources:
            if config_path.exists():
                self._config_cache[str(config_path)] = self._load_config_file(config_path)

        # 开始监控
        self.watcher.start_watching()

    def stop_watching(self):
        """停止监控配置变化"""
        self.watcher.stop_watching()

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self._lock:
            for config_data in self._config_cache.values():
                if key in config_data:
                    return config_data[key]
            return default

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            all_config = {}
            for source, config_data in self._config_cache.items():
                all_config.update(config_data)
            return all_config

    def reload_all_configs(self):
        """手动重新加载所有配置"""
        with self._lock:
            for config_path in self.config_sources:
                if config_path.exists():
                    self._reload_config_file(config_path)

            if self.reload_callback:
                self.reload_callback()


class HotReloadManager:
    """热重载管理器"""

    def __init__(self):
        self.config_reloader: Optional[ConfigurationReloader] = None
        self.module_watchers: Dict[str, ConfigurationWatcher] = {}
        self._active_modules: Set[str] = set()
        self._reload_callbacks: List[Callable[[str], None]] = []
        self._lock = threading.RLock()

    def setup_config_hot_reload(self, config_sources: List[str],
                                reload_callback: Optional[Callable[[], None]] = None):
        """设置配置热重载"""
        self.config_reloader = ConfigurationReloader(config_sources, reload_callback)
        self.config_reloader.start_watching()

    def setup_module_hot_reload(self, module_patterns: List[str],
                                reload_callback: Optional[Callable[[str], None]] = None):
        """设置模块热重载"""
        for pattern in module_patterns:
            if pattern not in self.module_watchers:
                # 创建监控器
                watcher = ConfigurationWatcher([pattern], check_interval=1.0)

                # 添加模块重载处理器
                if reload_callback:
                    watcher.add_change_handler(lambda change, cb=reload_callback: cb(change.key))

                self.module_watchers[pattern] = watcher
                self._active_modules.add(pattern)
                watcher.start_watching()

    def register_reload_callback(self, callback: Callable[[str], None]):
        """注册重载回调"""
        with self._lock:
            self._reload_callbacks.append(callback)

    def unregister_reload_callback(self, callback: Callable[[str], None]) -> bool:
        """取消注册重载回调"""
        with self._lock:
            if callback in self._reload_callbacks:
                self._reload_callbacks.remove(callback)
                return True
            return False

    def _notify_reload_callbacks(self, source: str):
        """通知所有重载回调"""
        with self._lock:
            for callback in self._reload_callbacks:
                try:
                    callback(source)
                except Exception as e:
                    print(f"Reload callback error: {e}")

    def is_watching(self, source: str) -> bool:
        """检查是否在监控指定源"""
        return (self.config_reloader and source in [str(p) for p in self.config_reloader.config_sources]) or \
            (source in self._active_modules)

    def get_watched_sources(self) -> List[str]:
        """获取所有监控的源"""
        sources = []

        if self.config_reloader:
            sources.extend([str(p) for p in self.config_reloader.config_sources])

        sources.extend(list(self._active_modules))
        return sources

    def stop_all_watching(self):
        """停止所有监控"""
        if self.config_reloader:
            self.config_reloader.stop_watching()
            self.config_reloader = None

        for watcher in self.module_watchers.values():
            watcher.stop_watching()

        self.module_watchers.clear()
        self._active_modules.clear()

    def force_reload(self, source: str):
        """强制重新加载指定源"""
        if self.config_reloader and source in [str(p) for p in self.config_reloader.config_sources]:
            self.config_reloader.reload_all_configs()
        elif source in self._active_modules:
            self._notify_reload_callbacks(source)

    def get_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        return {
            'config_watching': self.config_reloader is not None,
            'module_watching': len(self._active_modules),
            'watched_sources': self.get_watched_sources(),
            'callback_count': len(self._reload_callbacks)
        }


# 全局热重载管理器实例
hot_reload_manager = HotReloadManager()
