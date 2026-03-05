"""代理池抽象接口

定义代理源的抽象基类和数据结构，
现有代理代码需适配此接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ProxyProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyInfo:
    host: str
    port: int
    protocol: ProxyProtocol
    username: str | None = None
    password: str | None = None
    region: str | None = None
    expire_at: float | None = None
    fail_count: int = 0
    last_used: float = 0

    @property
    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"


class BaseProxyProvider(ABC):
    """代理源抽象基类，现有代码需适配此接口"""

    @abstractmethod
    async def fetch_proxies(
        self,
        count: int = 10,
        protocol: ProxyProtocol = ProxyProtocol.HTTP,
    ) -> list[ProxyInfo]:
        ...

    @abstractmethod
    async def report_invalid(self, proxy: ProxyInfo) -> None:
        ...
