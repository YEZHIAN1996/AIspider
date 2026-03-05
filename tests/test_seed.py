"""种子去重测试"""
import pytest
from src.seed.dedup import BloomDeduplicator


@pytest.mark.asyncio
async def test_bloom_dedup(redis_client):
    """测试布隆过滤器去重"""
    dedup = BloomDeduplicator(redis_client, "test_bloom")

    url = "https://example.com/page/1"
    assert await dedup.check_and_add(url) is True
    assert await dedup.check_and_add(url) is False
    assert await dedup.exists(url) is True
