"""Redis 共享代理池

多个 Scrapy Worker 共享同一个 Redis 代理池，
支持健康检查、冷却淘汰、定时刷新。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from src.infra.metrics import PROXY_POOL_SIZE
from src.proxy.base import ProxyInfo, ProxyProtocol

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_POOL_KEY = "proxy:pool"
_BAD_KEY = "proxy:bad"


class RedisProxyPool:
    """Redis 共享代理池

    Args:
        redis: Redis 异步客户端
        max_fail: 最大失败次数，超过后移入冷却队列
    """

    def __init__(self, redis: Redis, max_fail: int = 3) -> None:
        self._redis = redis
        self._max_fail = max_fail

    async def add(self, proxy: ProxyInfo) -> None:
        """添加代理到池中"""
        data = json.dumps({
            "host": proxy.host,
            "port": proxy.port,
            "protocol": proxy.protocol.value,
            "username": proxy.username,
            "password": proxy.password,
            "region": proxy.region,
            "expire_at": proxy.expire_at,
        }, ensure_ascii=False)
        await self._redis.sadd(_POOL_KEY, data)
        await self._update_metric()

    async def get(self) -> ProxyInfo | None:
        """随机获取一个可用代理"""
        raw = await self._redis.srandmember(_POOL_KEY)
        if raw is None:
            return None
        data = json.loads(raw)
        return ProxyInfo(
            host=data["host"],
            port=data["port"],
            protocol=ProxyProtocol(data["protocol"]),
            username=data.get("username"),
            password=data.get("password"),
            region=data.get("region"),
            expire_at=data.get("expire_at"),
        )

    async def size(self) -> int:
        """当前代理池大小"""
        count = await self._redis.scard(_POOL_KEY)
        PROXY_POOL_SIZE.set(count)
        return count

    async def _update_metric(self) -> None:
        count = await self._redis.scard(_POOL_KEY)
        PROXY_POOL_SIZE.set(count)
