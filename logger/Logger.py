from __future__ import annotations

from enum import IntEnum
from datetime import datetime
import os
from typing import Optional
from pathlib import Path
from dotenv import dotenv_values


class LogLevel(IntEnum):
    """日志级别定义，数值越大优先级越高。

    DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50)
    """

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


_LEVEL_NAME_MAP = {
    "DEBUG": LogLevel.DEBUG,
    "INFO": LogLevel.INFO,
    "WARN": LogLevel.WARNING,  # 常见别名
    "WARNING": LogLevel.WARNING,
    "ERROR": LogLevel.ERROR,
    "CRITICAL": LogLevel.CRITICAL,
}


def _parse_level(level: str | int | LogLevel | None) -> LogLevel:
    """将字符串/整数/枚举转换为 LogLevel。默认 INFO。"""
    if level is None:
        return LogLevel.INFO
    if isinstance(level, LogLevel):
        return level
    if isinstance(level, int):
        # 容错：接近标准 logging 的数值也可以被识别
        for lv in LogLevel:
            if level == lv.value:
                return lv
        # 不匹配则按阈值粗略映射
        if level <= LogLevel.DEBUG:
            return LogLevel.DEBUG
        if level <= LogLevel.INFO:
            return LogLevel.INFO
        if level <= LogLevel.WARNING:
            return LogLevel.WARNING
        if level <= LogLevel.ERROR:
            return LogLevel.ERROR
        return LogLevel.CRITICAL
    # 字符串处理
    s = str(level).strip().upper()
    return _LEVEL_NAME_MAP.get(s, LogLevel.INFO)


def _find_env_file() -> Optional[Path]:
    """在当前文件上层路径中寻找 .env 文件（最多向上查找 4 层）。"""
    base = Path(__file__).resolve().parent
    for p in [base, base.parent, base.parent.parent, base.parent.parent.parent]:
        candidate = p / ".env"
        if candidate.exists():
            return candidate
    return None


def _load_env_log_level() -> Optional[str]:
    """直接从 .env 中读取 LOG_LEVEL（不依赖进程环境变量）。"""
    env_path = _find_env_file()
    if env_path is None:
        return None
    values = dotenv_values(env_path)
    return values.get("LOG_LEVEL")


class LogManager:
    """日志管理器：统一控制全局日志级别并按需创建/管理 Logger。

    用法示例：
    >>> manager = LogManager()  # 从环境变量 LOG_LEVEL 读取，默认 INFO
    >>> logger = manager.get_logger("LogAnalyzer")
    >>> logger.info("分析开始…")
    >>> manager.set_level("ERROR")  # 动态提升阈值：仅打印 ERROR 及以上
    >>> logger.debug("这条不会打印")
    """

    def __init__(self, level: str | int | LogLevel | None = None):
        # 直接从 .env 读取 LOG_LEVEL（若无则回退到传入的 level 或默认 INFO）
        env_level = _load_env_log_level()
        base_level = _parse_level(level if level is not None else env_level)
        self._level: LogLevel = base_level
        self._loggers: dict[str, Logger] = {}

    @property
    def level(self) -> LogLevel:
        return self._level

    def set_level(self, level: str | int | LogLevel) -> None:
        """设置全局日志级别，并同步生效于已注册的 Logger（若它们未设置自己的覆盖级别）。"""
        self._level = _parse_level(level)

    def get_logger(self, name: str, level: Optional[str | int | LogLevel] = None) -> "Logger":
        """获取（或创建）一个命名 Logger。

        - name：模块/组件名（会出现在输出中）
        - level：可选，单独覆盖该 Logger 的阈值；不传则随管理器全局阈值
        """
        if name in self._loggers:
            logger = self._loggers[name]
            if level is not None:
                logger.set_level(level)
            return logger
        logger = Logger(name=name, manager=self, level=level)
        self._loggers[name] = logger
        return logger


class Logger:
    """轻量日志器：按阈值打印消息，支持常见五种级别。

    - 线程安全与文件写入不在本实现范围内；若有需要可扩展。
    - 为兼容已有代码，所有方法支持 `end` 与 `flush` 参数（类似 print）。
    """

    def __init__(self, name: str, manager: LogManager, level: Optional[str | int | LogLevel] = None):
        self._name = name
        self._manager = manager
        self._level_override: Optional[LogLevel] = _parse_level(level) if level is not None else None

    @property
    def name(self) -> str:
        return self._name

    @property
    def effective_level(self) -> LogLevel:
        return self._level_override if self._level_override is not None else self._manager.level

    def set_level(self, level: str | int | LogLevel | None) -> None:
        """为当前 Logger 设置覆盖级别；传 None 则恢复跟随管理器。"""
        self._level_override = _parse_level(level) if level is not None else None

    def enabled_for(self, level: LogLevel) -> bool:
        return level >= self.effective_level

    # 基础输出
    def log(self, level: LogLevel, message: str, *, end: str = "\n", flush: bool = False) -> None:
        if not self.enabled_for(level):
            return
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{time_str}] [{level.name}] [{self._name}] "
        print(prefix + message, end=end, flush=flush)

    # 便捷方法
    def debug(self, message: str, *, end: str = "\n", flush: bool = False) -> None:
        self.log(LogLevel.DEBUG, message, end=end, flush=flush)

    def info(self, message: str, *, end: str = "\n", flush: bool = False) -> None:
        self.log(LogLevel.INFO, message, end=end, flush=flush)

    def warning(self, message: str, *, end: str = "\n", flush: bool = False) -> None:
        self.log(LogLevel.WARNING, message, end=end, flush=flush)

    # 常见别名
    warn = warning

    def error(self, message: str, *, end: str = "\n", flush: bool = False) -> None:
        self.log(LogLevel.ERROR, message, end=end, flush=flush)

    def critical(self, message: str, *, end: str = "\n", flush: bool = False) -> None:
        self.log(LogLevel.CRITICAL, message, end=end, flush=flush)


# 提供一个默认的全局管理器与工厂函数，便于快速使用
_default_manager: Optional[LogManager] = None


def get_log_manager(level: Optional[str | int | LogLevel] = None) -> LogManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = LogManager(level)
    elif level is not None:
        _default_manager.set_level(level)
    return _default_manager


def get_logger(name: str, level: Optional[str | int | LogLevel] = None) -> Logger:
    manager = get_log_manager()
    return manager.get_logger(name, level=level)