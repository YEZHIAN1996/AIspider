"""写入缓冲 + 背压机制

缓冲数据到达阈值或超时后批量刷写，
缓冲区超过 2 倍阈值时触发背压拒绝写入。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Coroutine

from src.infra.metrics import WRITE_BUFFER_SIZE

logger = logging.getLogger(__name__)

# 批量写入回调类型
FlushCallback = Callable[[list[dict]], Coroutine]


class WriteBuffer:
    """写入缓冲器

    Args:
        name: 缓冲器名称（用于指标标签）
        flush_callback: 批量刷写回调函数
        max_size: 最大缓冲条数，达到后自动刷写
        flush_interval: 最大等待秒数，超时后自动刷写
    """

    def __init__(
        self,
        name: str,
        flush_callback: FlushCallback,
        max_size: int = 1000,
        flush_interval: float = 5.0,
    ) -> None:
        self._name = name
        self._flush_callback = flush_callback
        self._max_size = max_size
        self._flush_interval = flush_interval
        self._buffer: list[dict] = []
        self._lock = asyncio.Lock()
        self._timer_task: asyncio.Task | None = None

    async def add(self, item: dict) -> bool:
        """添加数据到缓冲区

        Returns:
            True = 成功, False = 背压拒绝
        """
        async with self._lock:
            if len(self._buffer) >= self._max_size * 2:
                logger.warning(
                    "缓冲区背压: name=%s, size=%d",
                    self._name, len(self._buffer),
                )
                return False

            self._buffer.append(item)
            WRITE_BUFFER_SIZE.labels(target=self._name).set(len(self._buffer))

            if len(self._buffer) >= self._max_size:
                await self._flush()

            # 启动定时刷写
            if self._timer_task is None or self._timer_task.done():
                self._timer_task = asyncio.create_task(self._timer_flush())

            return True

    async def flush(self) -> None:
        """手动触发刷写"""
        async with self._lock:
            await self._flush()

    async def _flush(self) -> None:
        """内部刷写（需在锁内调用）

        写入失败时将 batch 放回缓冲区头部，防止数据丢失。
        """
        if not self._buffer:
            return
        batch, self._buffer = self._buffer[:], []
        WRITE_BUFFER_SIZE.labels(target=self._name).set(0)

        try:
            await self._flush_callback(batch)
        except Exception:
            # 写入失败，将 batch 放回缓冲区头部
            self._buffer = batch + self._buffer
            WRITE_BUFFER_SIZE.labels(target=self._name).set(
                len(self._buffer)
            )
            logger.exception(
                "缓冲区刷写失败，数据已放回缓冲区: name=%s, batch_size=%d",
                self._name, len(batch),
            )

    async def _timer_flush(self) -> None:
        """定时刷写，防止数据在缓冲区停留过久"""
        await asyncio.sleep(self._flush_interval)
        async with self._lock:
            await self._flush()
