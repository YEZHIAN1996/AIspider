"""ZSET 优先级队列

基于 Redis Sorted Set 实现种子优先级队列，
score 越高优先级越高，支持批量出队。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.infra.metrics import (
    SEED_DEQUEUED_TOTAL,
    SEED_QUEUE_SIZE,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class SeedQueue:
    """基于 Redis ZSET 的优先级种子队列"""

    def __init__(self, redis: Redis, spider_name: str) -> None:
        self._redis = redis
        self._spider_name = spider_name
        self._key = f"queue:{spider_name}"

    @property
    def key(self) -> str:
        return self._key

    async def size(self) -> int:
        """当前队列长度"""
        count = await self._redis.zcard(self._key)
        SEED_QUEUE_SIZE.labels(
            spider_name=self._spider_name,
        ).set(count)
        return count

    async def pop(self, count: int = 1) -> list[str]:
        """弹出优先级最高的 N 条种子

        使用 ZPOPMAX 保证原子性。
        """
        results = await self._redis.zpopmax(self._key, count)
        seeds = [member for member, _score in results]
        if seeds:
            SEED_DEQUEUED_TOTAL.labels(
                spider_name=self._spider_name,
            ).inc(len(seeds))
        return seeds

    async def peek(self, count: int = 10) -> list[tuple[str, float]]:
        """查看队列头部（不弹出）"""
        return await self._redis.zrevrange(
            self._key, 0, count - 1, withscores=True,
        )

    async def clear(self) -> int:
        """清空队列"""
        return await self._redis.delete(self._key)
