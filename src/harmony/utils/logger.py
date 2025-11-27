"""Harmony框架日志系统"""

import json
import logging
import sys
import time
from enum import Enum
from typing import Optional, Dict, Any


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class HarmonyLogger:
    """Harmony框架专用日志记录器"""

    _loggers: Dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def configure(cls, level: LogLevel = LogLevel.INFO,
                  format_string: Optional[str] = None,
                  enable_colors: bool = True) -> None:
        """配置日志系统"""
        if cls._configured:
            return

        # 创建格式器
        if enable_colors:
            try:
                from colorlog import ColoredFormatter
                # 如果有colorlog，使用带颜色的格式
                format_string = format_string or "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                formatter = ColoredFormatter(
                    format_string,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    }
                )
            except ImportError:
                # 如果没有colorlog，使用标准格式（不带颜色）
                format_string = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
        else:
            # 不启用颜色时使用标准格式
            format_string = format_string or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')

        # 配置根日志记录器
        root_logger = logging.getLogger('harmony')
        root_logger.setLevel(getattr(logging, level.value))

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取日志记录器"""
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            logger = logging.getLogger(f'harmony.{name}')
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def log_method_call(cls, logger: logging.Logger, method_name: str,
                        args: tuple = (), kwargs: dict = None) -> None:
        """记录方法调用"""
        kwargs = kwargs or {}
        logger.debug(f"Calling method: {method_name} with args={args}, kwargs={kwargs}")

    @classmethod
    def log_method_return(cls, logger: logging.Logger, method_name: str,
                          result: Any = None, execution_time: Optional[float] = None) -> None:
        """记录方法返回"""
        time_info = f" (took {execution_time:.3f}s)" if execution_time else ""
        logger.debug(f"Method {method_name} returned{time_info}: {result}")

    @classmethod
    def log_exception(cls, logger: logging.Logger, method_name: str,
                      exception: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """记录异常"""
        error_msg = f"Exception in {method_name}: {type(exception).__name__}: {exception}"
        if context:
            error_msg += f" | Context: {json.dumps(context, default=str)}"
        logger.error(error_msg, exc_info=True)


class MethodTimer:
    """方法执行时间装饰器"""

    def __init__(self, logger: Optional[logging.Logger] = None,
                 log_level: LogLevel = LogLevel.DEBUG):
        self.logger = logger
        self.log_level = log_level

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            method_name = f"{func.__module__}.{func.__qualname__}"

            if self.logger:
                HarmonyLogger.log_method_call(self.logger, method_name, args, kwargs)

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                if self.logger:
                    HarmonyLogger.log_method_return(self.logger, method_name, result, execution_time)

                return result
            except Exception as e:
                if self.logger:
                    HarmonyLogger.log_exception(self.logger, method_name, e)
                raise

        return wrapper


def get_logger(name: str) -> logging.Logger:
    """便捷方法：获取日志记录器"""
    return HarmonyLogger.get_logger(name)


def log_execution_time(logger: Optional[logging.Logger] = None):
    """便捷装饰器：记录方法执行时间"""
    return MethodTimer(logger)


# 性能监控
class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.logger = get_logger('performance')
        self.timings: Dict[str, list] = {}

    def start_timer(self, operation: str) -> float:
        """开始计时"""
        start_time = time.time()
        return start_time

    def end_timer(self, operation: str, start_time: float) -> float:
        """结束计时并记录"""
        execution_time = time.time() - start_time

        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(execution_time)

        # 记录日志
        if len(self.timings[operation]) == 1 or execution_time > 1.0:  # 首次记录或执行时间超过1秒
            self.logger.info(f"Operation '{operation}' took {execution_time:.3f}s")

        return execution_time

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """获取统计信息"""
        stats = {}
        for operation, times in self.timings.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'total': sum(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
        return stats


# 全局性能监控器
performance_monitor = PerformanceMonitor()
