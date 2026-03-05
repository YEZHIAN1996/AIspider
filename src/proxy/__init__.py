"""代理池模块公共接口"""

from src.proxy.base import BaseProxyProvider, ProxyInfo, ProxyProtocol
from src.proxy.pool import RedisProxyPool

__all__ = [
    "BaseProxyProvider",
    "ProxyInfo",
    "ProxyProtocol",
    "RedisProxyPool",
]
