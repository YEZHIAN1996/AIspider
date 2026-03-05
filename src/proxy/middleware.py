"""Scrapy 代理中间件

从 Redis 共享代理池获取代理注入请求，
失败时上报代理池进行淘汰。
"""

from __future__ import annotations

import logging
from redis.asyncio import Redis
from src.proxy.pandas_provider import PandasProxyProvider
from src.proxy.base import ProxyProtocol

logger = logging.getLogger(__name__)


class PandasProxyMiddleware:
    """熊猫代理中间件"""

    def __init__(self, redis: Redis, redis_key: str = "pandas_proxy"):
        self.provider = PandasProxyProvider(redis, redis_key)

    @classmethod
    def from_crawler(cls, crawler):
        redis = crawler.spider._conn_manager.redis
        redis_key = crawler.settings.get("PANDAS_PROXY_KEY", "pandas_proxy")
        return cls(redis, redis_key)

    async def process_request(self, request, spider):
        proxies = await self.provider.fetch_proxies(count=1, protocol=ProxyProtocol.HTTP)
        if proxies:
            request.meta["proxy"] = proxies[0].url
            request.meta["_proxy_info"] = proxies[0]

    async def process_exception(self, request, exception, spider):
        if "_proxy_info" in request.meta:
            await self.provider.report_invalid(request.meta["_proxy_info"])
            logger.warning(f"代理失效已移除: {request.meta['_proxy_info'].host}")
