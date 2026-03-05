"""调度器测试"""
import pytest
from src.scheduler.tasks import SchedulerTask


def test_task_creation():
    """测试任务创建"""
    task = SchedulerTask(
        name="test_spider",
        spider_name="example_spider",
        schedule_type="cron",
        cron_expr="0 */6 * * *"
    )
    assert task.name == "test_spider"
    assert task.enabled is True


def test_task_validation():
    """测试任务校验"""
    with pytest.raises(ValueError):
        SchedulerTask(
            name="invalid",
            spider_name="test",
            schedule_type="cron",
            cron_expr="invalid_cron"
        )
