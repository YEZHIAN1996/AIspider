"""代理池测试"""
import pytest
from unittest.mock import AsyncMock
from src.proxy.pool import RedisProxyPool
from src.proxy.base import ProxyInfo, ProxyProtocol


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.sadd = AsyncMock()
    redis.srandmember = AsyncMock()
    redis.scard = AsyncMock(return_value=10)
    return redis


@pytest.mark.asyncio
async def test_add_proxy(mock_redis):
    pool = RedisProxyPool(mock_redis)
    proxy = ProxyInfo(host="1.2.3.4", port=8080, protocol=ProxyProtocol.HTTP)
    await pool.add(proxy)
    assert mock_redis.sadd.called


@pytest.mark.asyncio
async def test_get_proxy(mock_redis):
    import json
    mock_redis.srandmember = AsyncMock(return_value=json.dumps({
        "host": "1.2.3.4",
        "port": 8080,
        "protocol": "http"
    }))

    pool = RedisProxyPool(mock_redis)
    proxy = await pool.get()
    assert proxy is not None
    assert proxy.host == "1.2.3.4"


@pytest.mark.asyncio
async def test_pool_size(mock_redis):
    pool = RedisProxyPool(mock_redis)
    size = await pool.size()
    assert size == 10
