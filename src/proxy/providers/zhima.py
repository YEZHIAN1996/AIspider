"""芝麻代理供应商"""
from __future__ import annotations
import httpx
from src.proxy.base import ProxyInfo, ProxyProtocol
from src.proxy.providers import ProxyProvider


class ZhimaProvider(ProxyProvider):
    """芝麻代理供应商"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://webapi.http.zhimacangku.com"

    async def fetch_proxies(self) -> list[ProxyInfo]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/getip",
                params={"num": 100, "type": 2, "pro": 0, "city": 0, "yys": 0, "port": 1, "time": 1, "ts": 1, "ys": 1, "cs": 1, "lb": 1, "sb": 0, "pb": 4, "mr": 1, "regions": ""}
            )
            data = resp.json()
            proxies = []
            for item in data.get("data", []):
                proxies.append(ProxyInfo(host=item["ip"], port=item["port"], protocol=ProxyProtocol.HTTP))
            return proxies

    async def check_balance(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/getbalance", params={"api": self.api_key})
            return resp.json()
