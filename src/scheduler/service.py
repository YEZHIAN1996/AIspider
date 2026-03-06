"""Scheduler API-side service.

API 进程通过该服务读写任务配置，并通过 Redis 命令队列请求
独立 scheduler 进程执行 start/stop。
"""

from __future__ import annotations

import json
import time
import uuid

from src.config import get_settings
from src.infra.utils import safe_json_decode
from src.scheduler.tasks import (
    SpiderTask,
    TaskStore,
    TaskValidationError,
    extract_seed_urls,
    validate_schedule,
)

COMMAND_KEY = "scheduler:commands"
RUNTIME_STATUS_KEY = "scheduler:runtime_status"
COMMAND_STATUS_KEY = "scheduler:command_status:{command_id}"


class TaskService:
    """任务服务（API 进程使用）"""

    def __init__(self, redis) -> None:
        self._redis = redis
        self._task_store = TaskStore(redis)

    async def list_tasks(self) -> list[SpiderTask]:
        return await self._task_store.get_all()

    async def create_task(
        self,
        spider_name: str,
        schedule_type: str,
        schedule_expr: str,
        spider_args: list[str],
    ) -> SpiderTask:
        validate_schedule(schedule_type, schedule_expr)
        # 允许 spider_args 为空（支持自带 start_requests 的爬虫）
        task = SpiderTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            spider_name=spider_name,
            schedule_type=schedule_type,
            schedule_expr=schedule_expr,
            spider_args=spider_args,
        )
        await self._task_store.save(task)
        return task

    async def update_task(
        self,
        task_id: str,
        schedule_type: str | None = None,
        schedule_expr: str | None = None,
        enabled: bool | None = None,
        spider_args: list[str] | None = None,
    ) -> SpiderTask | None:
        task = await self._task_store.get(task_id)
        if task is None:
            return None
        if schedule_type is not None:
            task.schedule_type = schedule_type
        if schedule_expr is not None:
            task.schedule_expr = schedule_expr
        if enabled is not None:
            task.enabled = enabled
        if spider_args is not None:
            task.spider_args = spider_args

        validate_schedule(task.schedule_type, task.schedule_expr)
        urls = extract_seed_urls(task.spider_args)
        if not urls:
            raise TaskValidationError(
                "spider_args must include at least one valid http/https URL"
            )
        await self._task_store.save(task)
        return task

    async def get_task(self, task_id: str) -> SpiderTask | None:
        return await self._task_store.get(task_id)

    async def delete_task(self, task_id: str) -> bool:
        task = await self._task_store.get(task_id)
        if task is None:
            return False
        await self._task_store.delete(task_id)
        return True

    async def request_start(self, task_id: str) -> str:
        return await self._push_command("run_task", task_id)

    async def request_stop(self, task_id: str) -> str:
        # 停止请求先持久化 disabled，避免“请求发出后仍继续调度”窗口
        task = await self._task_store.get(task_id)
        if task is not None and task.enabled:
            task.enabled = False
            await self._task_store.save(task)
        return await self._push_command("stop_task", task_id)

    async def get_command_status(self, command_id: str) -> dict:
        raw = await self._redis.get(
            COMMAND_STATUS_KEY.format(command_id=command_id)
        )
        return safe_json_decode(raw, {"command_id": command_id, "status": "unknown"})

    async def get_runtime_status(self) -> dict:
        raw = await self._redis.get(RUNTIME_STATUS_KEY)
        return safe_json_decode(raw, {"updated_at": 0.0, "processes": []})

    async def _push_command(self, command: str, task_id: str) -> str:
        settings = get_settings()
        command_id = uuid.uuid4().hex
        payload = json.dumps(
            {
                "command_id": command_id,
                "command": command,
                "task_id": task_id,
                "requested_at": time.time(),
            },
            ensure_ascii=False,
        )
        initial_status = json.dumps(
            {
                "command_id": command_id,
                "command": command,
                "task_id": task_id,
                "status": "queued",
                "updated_at": time.time(),
            },
            ensure_ascii=False,
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.rpush(COMMAND_KEY, payload)
            await pipe.set(
                COMMAND_STATUS_KEY.format(command_id=command_id),
                initial_status,
                ex=settings.scheduler_command_status_ttl_seconds,
            )
            await pipe.execute()
        return command_id
