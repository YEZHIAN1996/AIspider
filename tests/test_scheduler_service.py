"""调度服务测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.scheduler.service import TaskService
from src.scheduler.tasks import SpiderTask


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.rpush = AsyncMock()
    redis.pipeline = MagicMock()
    return redis


@pytest.mark.asyncio
async def test_create_task(mock_redis):
    service = TaskService(mock_redis)
    task = await service.create_task(
        spider_name="test_spider",
        schedule_type="cron",
        schedule_expr="0 */6 * * *",
        spider_args=["https://example.com"]
    )
    assert task.spider_name == "test_spider"
    assert task.enabled is True


@pytest.mark.asyncio
async def test_create_task_no_urls(mock_redis):
    service = TaskService(mock_redis)
    with pytest.raises(Exception):
        await service.create_task(
            spider_name="test",
            schedule_type="cron",
            schedule_expr="0 0 * * *",
            spider_args=["no_url_here"]
        )


@pytest.mark.asyncio
async def test_request_start(mock_redis):
    service = TaskService(mock_redis)
    command_id = await service.request_start("task_123")
    assert command_id is not None
    assert len(command_id) > 0
