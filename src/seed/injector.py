"""种子注入器

负责将种子 URL 批量注入到 Redis 队列，
支持去重检查、优先级设置、trace_id 生成。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from src.infra.metrics import (
    SEED_DUPLICATED_TOTAL,
    SEED_ENQUEUED_TOTAL,
)
from src.seed.dedup import Deduplicator
from src.seed.queue import SeedQueue

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class SeedMeta:
    """种子元数据"""
    url: str
    spider_name: str
    priority: float = 5.0
    seed_type: str = "once"  # once | periodic
    max_retry: int = 3
    inject_time: float = field(default_factory=time.time)
    ttl: int = 86400
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)


class SeedInjector:
    """种子注入器，负责批量注入种子到 Redis"""

    def __init__(self, redis: Redis, spider_name: str) -> None:
        self._redis = redis
        self._spider_name = spider_name
        self._dedup = Deduplicator(redis, spider_name)
        self._queue = SeedQueue(redis, spider_name)

    @property
    def queue(self) -> SeedQueue:
        return self._queue

    @property
    def dedup(self) -> Deduplicator:
        return self._dedup

    async def init(self, bloom_capacity: int = 10_000_000) -> None:
        """初始化去重器（Bloom Filter）"""
        await self._dedup.init_bloom(capacity=bloom_capacity)

    async def inject(self, seed: SeedMeta) -> bool:
        """注入单条种子

        Returns:
            True = 注入成功, False = 重复跳过
        """
        seed_json = json.dumps(asdict(seed), ensure_ascii=False)
        added = await self._dedup.check_and_add(
            url=seed.url,
            priority=seed.priority,
            seed_json=seed_json,
            queue_key=self._queue.key,
            ttl=seed.ttl,
        )
        if added:
            SEED_ENQUEUED_TOTAL.labels(
                spider_name=self._spider_name,
            ).inc()
            return True

        SEED_DUPLICATED_TOTAL.labels(
            spider_name=self._spider_name,
        ).inc()
        return False

    async def inject_batch(
        self,
        seeds: list[SeedMeta],
        batch_size: int = 500,
    ) -> dict[str, int]:
        """批量注入种子

        Args:
            seeds: 种子列表
            batch_size: 每批处理数量

        Returns:
            {"added": N, "duplicated": M}
        """
        added = 0
        duplicated = 0

        for i in range(0, len(seeds), batch_size):
            batch = seeds[i : i + batch_size]
            for seed in batch:
                if await self.inject(seed):
                    added += 1
                else:
                    duplicated += 1

        logger.info(
            "批量注入完成: spider=%s, added=%d, duplicated=%d",
            self._spider_name, added, duplicated,
        )
        return {"added": added, "duplicated": duplicated}
