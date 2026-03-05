"""熊猫代理适配器"""
from __future__ import annotations
import time
from src.proxy.base import BaseProxyProvider, ProxyInfo, ProxyProtocol
from redis.asyncio import Redis


class PandasProxyProvider(BaseProxyProvider):
    """熊猫代理适配 AIspider 接口"""

    def __init__(self, redis: Redis, redis_key: str = "pandas_proxy"):
        self.redis = redis
        self.redis_key = redis_key

    async def fetch_proxies(self, count: int = 10, protocol: ProxyProtocol = ProxyProtocol.HTTP) -> list[ProxyInfo]:
        """从 Redis 获取可用代理"""
        now = int(time.time())
        proxies = await self.redis.zrangebyscore(
            self.redis_key, now, '+inf', start=0, num=count, withscores=True
        )

        result = []
        for proxy_bytes, expire_ts in proxies:
            proxy_str = proxy_bytes.decode() if isinstance(proxy_bytes, bytes) else proxy_bytes
            ip, port = proxy_str.split(':')
            result.append(ProxyInfo(
                host=ip,
                port=int(port),
                protocol=protocol,
                expire_at=expire_ts
            ))
        return result

    async def report_invalid(self, proxy: ProxyInfo) -> None:
        """移除失效代理"""
        proxy_str = f"{proxy.host}:{proxy.port}"
        await self.redis.zrem(self.redis_key, proxy_str)
