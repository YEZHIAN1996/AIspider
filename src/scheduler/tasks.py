"""任务定义与持久化

定义调度任务的数据结构，
支持从 Redis/PG 加载和持久化任务配置。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse
from typing import TYPE_CHECKING

from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Redis key 前缀
_TASK_KEY = "scheduler:tasks"


class TaskValidationError(ValueError):
    """任务参数校验失败"""


def validate_schedule(schedule_type: str, schedule_expr: str) -> None:
    """校验调度表达式合法性。"""
    if schedule_type not in {"cron", "interval"}:
        raise TaskValidationError("schedule_type must be 'cron' or 'interval'")

    if schedule_type == "cron":
        parts = schedule_expr.split()
        if len(parts) != 5:
            raise TaskValidationError(
                "cron schedule_expr must contain 5 fields"
            )
        try:
            CronTrigger.from_crontab(schedule_expr)
        except Exception as exc:
            raise TaskValidationError(
                f"invalid cron expression: {schedule_expr}"
            ) from exc
        return

    # interval
    try:
        seconds = int(schedule_expr)
    except ValueError as exc:
        raise TaskValidationError(
            "interval schedule_expr must be an integer seconds string"
        ) from exc
    if seconds <= 0:
        raise TaskValidationError("interval schedule_expr must be > 0")


def extract_seed_urls(spider_args: list[str]) -> list[str]:
    """从 spider_args 提取有效 URL。"""
    urls: list[str] = []
    for arg in spider_args:
        if not isinstance(arg, str):
            continue
        value = arg.strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            urls.append(value)
    return urls


@dataclass
class SpiderTask:
    """调度任务定义"""

    task_id: str
    spider_name: str
    schedule_type: str = "cron"  # cron | interval
    schedule_expr: str = ""     # cron: "0 */2 * * *", interval: "300"
    enabled: bool = True
    spider_args: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_run: float | None = None
    status: str = "idle"  # idle | running | paused


class TaskStore:
    """任务持久化存储（Redis HASH）"""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def save(self, task: SpiderTask) -> None:
        """保存任务到 Redis"""
        data = json.dumps(asdict(task), ensure_ascii=False)
        await self._redis.hset(_TASK_KEY, task.task_id, data)

    async def get(self, task_id: str) -> SpiderTask | None:
        """获取单个任务"""
        raw = await self._redis.hget(_TASK_KEY, task_id)
        if raw is None:
            return None
        return SpiderTask(**json.loads(raw))

    async def get_all(self) -> list[SpiderTask]:
        """获取所有任务"""
        all_raw = await self._redis.hgetall(_TASK_KEY)
        return [
            SpiderTask(**json.loads(v))
            for v in all_raw.values()
        ]

    async def delete(self, task_id: str) -> None:
        """删除任务"""
        await self._redis.hdel(_TASK_KEY, task_id)
