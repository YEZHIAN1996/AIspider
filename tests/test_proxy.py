"""代理池测试"""
import pytest
from src.proxy.pandas_provider import PandasProxyProvider
from src.proxy.base import ProxyInfo, ProxyProtocol


@pytest.mark.asyncio
async def test_fetch_proxies(redis_client):
    """测试获取代理"""
    provider = PandasProxyProvider(redis_client, "test_proxy")

    # 添加测试代理
    await redis_client.zadd("test_proxy", {"1.2.3.4:8080": 9999999999})

    proxies = await provider.fetch_proxies(count=1)
    assert len(proxies) == 1
    assert proxies[0].host == "1.2.3.4"
    assert proxies[0].port == 8080


@pytest.mark.asyncio
async def test_report_invalid(redis_client):
    """测试移除失效代理"""
    provider = PandasProxyProvider(redis_client, "test_proxy")

    await redis_client.zadd("test_proxy", {"1.2.3.4:8080": 9999999999})

    proxy = ProxyInfo(host="1.2.3.4", port=8080, protocol=ProxyProtocol.HTTP)
    await provider.report_invalid(proxy)

    count = await redis_client.zcard("test_proxy")
    assert count == 0
