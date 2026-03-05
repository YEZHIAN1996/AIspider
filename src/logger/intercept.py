"""stdlib logging 拦截器

将 Scrapy / Twisted / 第三方库的 stdlib logging
统一转发到 Loguru，实现日志格式统一。
"""

from __future__ import annotations

import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    """拦截 stdlib logging，转发到 Loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        # 映射 stdlib level 到 Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到实际调用者的栈深度
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


def intercept_stdlib_logging() -> None:
    """拦截所有 stdlib logging，统一转发到 Loguru

    应在应用启动时、setup_logger 之后调用。
    """
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=0,
        force=True,
    )
