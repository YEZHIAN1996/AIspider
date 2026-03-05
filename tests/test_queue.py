"""种子队列测试"""
import pytest
from src.seed.queue import SeedQueue


@pytest.mark.asyncio
async def test_seed_enqueue(redis_client):
    """测试种子入队"""
    queue = SeedQueue(redis_client, "test_queue")

    seed = {
        "url": "https://example.com",
        "spider_name": "test",
        "priority": 5
    }

    await queue.enqueue(seed, priority=5)
    size = await queue.size()
    assert size == 1


@pytest.mark.asyncio
async def test_seed_dequeue(redis_client):
    """测试种子出队"""
    queue = SeedQueue(redis_client, "test_queue")

    await queue.enqueue({"url": "https://example.com"}, priority=5)
    seed = await queue.dequeue()

    assert seed is not None
    assert "url" in seed
