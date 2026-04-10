"""
Logger 使用示例

运行：
    python logger/logger_demo.py

演示内容：
1. 全局日志级别控制（默认 INFO）
2. 单个 Logger 覆盖自身级别
3. 不同级别的输出示例
4. 兼容 print 的流式输出（end/flush）
"""

import time
from Logger import get_log_manager, get_logger, LogLevel


def main():
    # 初始化全局管理器，默认 INFO（也可从环境变量 LOG_LEVEL 读取）
    manager = get_log_manager()

    # 创建两个命名 Logger
    analyzer_logger = get_logger("LogAnalyzer")
    # fetcher_logger = get_logger("LogFetcher", level="ERROR")  # 覆盖为 ERROR
    fetcher_logger = get_logger("LogFetcher")  # 覆盖为 ERROR

    analyzer_logger.info("分析开始…")
    analyzer_logger.debug("这条不会显示（当前阈值为 INFO）")

    # 动态调整全局级别到 DEBUG
    # manager.set_level("DEBUG")
    analyzer_logger.debug("切到 DEBUG 后，调试日志生效")

    analyzer_logger.warning("可能存在异常或边界情况")
    analyzer_logger.error("发现错误，需进一步排查")

    # 单个 Logger 覆盖级别演示：仅 ERROR 及以上会输出
    fetcher_logger.info("这条不会打印（LogFetcher 级别为 ERROR）")
    fetcher_logger.error("日志提取组件发生错误")

    # 兼容流式输出：类似原来的 print(end='', flush=True)
    analyzer_logger.info("流式输出开始：", end="", flush=True)
    for i in range(3):
        analyzer_logger.info(f"{i}", end="", flush=True)
        time.sleep(0.2)
    analyzer_logger.info(" ← 完成\n", end="", flush=True)


if __name__ == "__main__":
    main()