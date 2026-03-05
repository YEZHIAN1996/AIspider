"""日志初始化模块

基于 Loguru 的统一日志配置，支持：
- JSON 结构化输出
- 异步写入（enqueue=True）
- 文件轮转与自动清理
- ERROR 单独文件
- 模块/spider 上下文绑定
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.config import get_settings


def setup_logger(
    module_name: str,
    spider_id: str | None = None,
) -> logger:
    """初始化日志，返回绑定了上下文的 logger 实例

    Args:
        module_name: 模块名称（seed / spider / writer 等）
        spider_id: 爬虫实例 ID，系统级模块传 None
    """
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认 handler，避免重复输出
    logger.remove()

    context = {
        "module": module_name,
        "spider_id": spider_id or "system",
    }

    # 1. 控制台输出（开发调试用）
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[module]}</cyan>:<cyan>{extra[spider_id]}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # 2. JSON 文件 — 全量日志
    logger.add(
        str(log_dir / f"{module_name}.log"),
        level="INFO",
        format="{message}",
        serialize=True,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="gz",
        enqueue=True,
    )

    # 3. ERROR 单独文件
    logger.add(
        str(log_dir / f"{module_name}_error.log"),
        level="ERROR",
        serialize=True,
        rotation="50 MB",
        retention="60 days",
        compression="gz",
        enqueue=True,
    )

    return logger.bind(**context)
