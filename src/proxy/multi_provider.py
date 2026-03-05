"""多供应商代理管理器"""
from __future__ import annotations
import asyncio
from src.proxy.providers import ProxyProvider
from src.proxy.pool import RedisProxyPool


class MultiProviderManager:
    """多供应商代理管理器，支持优先级和故障切换"""

    def __init__(self, pool: RedisProxyPool):
        self.pool = pool
        self.providers: list[tuple[int, ProxyProvider]] = []  # (priority, provider)

    def add_provider(self, provider: ProxyProvider, priority: int = 0):
        """添加供应商，priority 越大优先级越高"""
        self.providers.append((priority, provider))
        self.providers.sort(key=lambda x: x[0], reverse=True)

    async def refill(self):
        """按优先级从供应商获取代理并填充池"""
        for priority, provider in self.providers:
            try:
                proxies = await provider.fetch_proxies()
                for proxy in proxies:
                    await self.pool.add(proxy)
                return
            except Exception:
                continue
