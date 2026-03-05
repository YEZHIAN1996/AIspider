"""快代理供应商"""
from __future__ import annotations
import httpx
from src.proxy.base import ProxyInfo, ProxyProtocol
from src.proxy.providers import ProxyProvider


class KuaidailiProvider(ProxyProvider):
    """快代理供应商"""

    def __init__(self, api_key: str, order_id: str):
        self.api_key = api_key
        self.order_id = order_id
        self.base_url = "https://dps.kdlapi.com/api"

    async def fetch_proxies(self) -> list[ProxyInfo]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/getdps",
                params={"secret_id": self.api_key, "num": 100, "signature": self.order_id}
            )
            proxies = []
            for line in resp.text.strip().split("\n"):
                host, port = line.split(":")
                proxies.append(ProxyInfo(host=host, port=int(port), protocol=ProxyProtocol.HTTP))
            return proxies

    async def check_balance(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/getbalance", params={"secret_id": self.api_key})
            return resp.json()
