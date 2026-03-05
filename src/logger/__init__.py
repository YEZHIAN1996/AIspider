"""日志模块公共接口"""

from src.logger.setup import setup_logger
from src.logger.intercept import intercept_stdlib_logging
from src.logger.sinks import KafkaSink, SamplingFilter

__all__ = [
    "setup_logger",
    "intercept_stdlib_logging",
    "KafkaSink",
    "SamplingFilter",
]
