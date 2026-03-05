"""任务运行指标记录"""
from __future__ import annotations
import time
from dataclasses import dataclass, asdict
import json


@dataclass
class TaskMetrics:
    """任务运行指标"""
    task_id: str
    start_time: float
    end_time: float
    items_scraped: int
    items_success: int
    items_failed: int
    duration: float
    success_rate: float

    @classmethod
    def create(cls, task_id: str, start_time: float, items_scraped: int, items_success: int, items_failed: int):
        end_time = time.time()
        duration = end_time - start_time
        success_rate = items_success / items_scraped if items_scraped > 0 else 0.0
        return cls(
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            items_scraped=items_scraped,
            items_success=items_success,
            items_failed=items_failed,
            duration=duration,
            success_rate=success_rate
        )


class MetricsStore:
    """指标存储"""

    def __init__(self, redis):
        self._redis = redis

    async def save(self, metrics: TaskMetrics):
        key = f"task_metrics:{metrics.task_id}:{int(metrics.start_time)}"
        await self._redis.setex(key, 86400 * 7, json.dumps(asdict(metrics)))

    async def get_history(self, task_id: str, limit: int = 10) -> list[TaskMetrics]:
        pattern = f"task_metrics:{task_id}:*"
        keys = await self._redis.keys(pattern)
        keys = sorted(keys, reverse=True)[:limit]
        metrics = []
        for key in keys:
            data = await self._redis.get(key)
            if data:
                metrics.append(TaskMetrics(**json.loads(data)))
        return metrics
