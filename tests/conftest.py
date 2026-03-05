"""测试配置和 fixtures"""
import pytest
from redis.asyncio import Redis
from src.config import Settings


@pytest.fixture
def test_settings():
    """测试配置"""
    return Settings(
        redis_url="redis://localhost:6379/15",
        pg_dsn="postgresql://test:test@localhost:5432/test_aispider",
        kafka_brokers="localhost:9092",
        jwt_secret="test-secret"
    )


@pytest.fixture
async def redis_client(test_settings):
    """Redis 测试客户端"""
    client = Redis.from_url(test_settings.redis_url)
    yield client
    await client.flushdb()
    await client.close()
