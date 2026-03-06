"""Redis 死信队列

Kafka 发送失败的数据写入 Redis 死信队列，
后台任务定时重放，保证数据最终一致性。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from src.infra.metrics import DEAD_LETTER_SIZE

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# 死信队列 Redis key
_DLQ_KEY = "dlq:{target}"


class DeadLetterQueue:
    """Redis 死信队列

    写入失败的数据暂存到 Redis LIST，
    后台任务定时取出重放。

    Args:
        redis: Redis 异步客户端
        target: 目标标识（如 "kafka", "postgres"）
    """

    def __init__(self, redis: Redis, target: str = "kafka") -> None:
        self._redis = redis
        self._target = target
        self._key = _DLQ_KEY.format(target=target)

    async def push(self, item: dict, error: str = "") -> None:
        """将失败数据推入死信队列"""
        envelope = {
            "data": item,
            "error": error,
            "target": self._target,
            "failed_at": time.time(),
            "retry_count": 0,
        }
        payload = json.dumps(envelope, ensure_ascii=False)
        await self._redis.rpush(self._key, payload)
        size = await self._redis.llen(self._key)
        DEAD_LETTER_SIZE.set(size)

    async def pop(self, count: int = 100) -> list[dict]:
        """从死信队列取出数据用于重放

        Args:
            count: 每次取出的最大条数

        Returns:
            死信信封列表
        """
        items: list[dict] = []
        for _ in range(count):
            raw = await self._redis.lpop(self._key)
            if raw is None:
                break
            items.append(json.loads(raw))

        size = await self._redis.llen(self._key)
        DEAD_LETTER_SIZE.set(size)
        return items

    async def size(self) -> int:
        """当前死信队列积压量"""
        count = await self._redis.llen(self._key)
        DEAD_LETTER_SIZE.set(count)
        return count

    async def push_batch(self, items: list[dict], error: str = "") -> None:
        """批量推入死信队列"""
        if not items:
            return

        envelopes = [
            json.dumps({
                "data": item,
                "error": error,
                "target": self._target,
                "failed_at": time.time(),
                "retry_count": 0,
            }, ensure_ascii=False)
            for item in items
        ]

        await self._redis.rpush(self._key, *envelopes)
        size = await self._redis.llen(self._key)
        DEAD_LETTER_SIZE.set(size)
        logger.warning(
            "批量写入死信队列: target=%s, count=%d",
            self._target, len(items),
        )
