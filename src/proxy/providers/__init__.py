"""代理供应商抽象接口"""
from __future__ import annotations
from abc import ABC, abstractmethod
from src.proxy.base import ProxyInfo


class ProxyProvider(ABC):
    """代理供应商抽象接口"""

    @abstractmethod
    async def fetch_proxies(self) -> list[ProxyInfo]:
        """获取代理列表"""
        pass

    @abstractmethod
    async def check_balance(self) -> dict:
        """检查余额"""
        pass
