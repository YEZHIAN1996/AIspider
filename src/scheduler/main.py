"""APScheduler 调度器入口。

运行模型：
1. 独立 scheduler 进程持有 APScheduler。
2. API 仅写任务存储并通过 Redis 命令队列请求 run/stop。
3. scheduler 周期性对账任务配置并同步到 APScheduler。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
import uuid
from typing import TYPE_CHECKING

from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.infra.metrics import SCHEDULER_TASK_EXECUTIONS
from src.scheduler.lock import acquire_scheduler_lock, release_scheduler_lock
from src.scheduler.service import (
    COMMAND_KEY,
    COMMAND_STATUS_KEY,
    RUNTIME_STATUS_KEY,
)
from src.scheduler.tasks import SpiderTask, TaskStore, extract_seed_urls
from src.seed.injector import SeedInjector, SeedMeta

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)
PROCESSED_COMMAND_KEY = "scheduler:processed_command:{command_id}"
SUPPORTED_COMMANDS = {"run_task", "stop_task"}


class SpiderScheduler:
    """独立调度器。

    通过后台循环完成三件事：
    - 任务对账：同步 Redis TaskStore 和 APScheduler 内存态
    - 命令处理：执行 API 投递的 run_task/stop_task
    - 运行态上报：将执行状态写入 Redis 供 API 查询
    """

    def __init__(
        self,
        redis: Redis,
        command_status_ttl_seconds: int,
        command_dedupe_ttl_seconds: int,
    ) -> None:
        self._redis = redis
        self._task_store = TaskStore(redis)
        self._scheduler: AsyncScheduler | None = None
        self._running = False
        self._bg_tasks: list[asyncio.Task] = []
        self._schedule_cache: dict[str, tuple[str, str, bool, tuple[str, ...]]] = {}
        self._active_runs: dict[str, dict] = {}
        self._finished_runs: list[dict] = []
        self._command_status_ttl_seconds = command_status_ttl_seconds
        self._command_dedupe_ttl_seconds = command_dedupe_ttl_seconds

    @property
    def task_store(self) -> TaskStore:
        return self._task_store

    async def start(self) -> None:
        if self._running:
            return

        self._scheduler = AsyncScheduler()
        await self._scheduler.__aenter__()
        self._running = True

        await self._sync_schedules()
        await self._publish_runtime_status()

        self._bg_tasks = [
            asyncio.create_task(self._sync_loop()),
            asyncio.create_task(self._command_loop()),
            asyncio.create_task(self._status_loop()),
        ]
        logger.info("调度器已启动")

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        for task in self._bg_tasks:
            task.cancel()
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()

        await self._publish_runtime_status()

        if self._scheduler:
            await self._scheduler.__aexit__(None, None, None)
            self._scheduler = None
        logger.info("调度器已停止")

    async def _sync_loop(self) -> None:
        while self._running:
            try:
                await self._sync_schedules()
            except Exception:
                logger.exception("任务对账失败")
            await asyncio.sleep(5)

    async def _command_loop(self) -> None:
        while self._running:
            try:
                item = await self._redis.blpop(COMMAND_KEY, timeout=1)
                if not item:
                    continue
                _, raw = item
                if isinstance(raw, bytes):
                    raw = raw.decode()
                try:
                    command = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("丢弃非法命令 payload: %s", raw)
                    continue
                await self._handle_command(command)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("处理 scheduler 命令失败")

    async def _status_loop(self) -> None:
        while self._running:
            try:
                await self._publish_runtime_status()
            except Exception:
                logger.exception("发布运行状态失败")
            await asyncio.sleep(2)

    async def _publish_runtime_status(self) -> None:
        processes = [
            {
                "spider_name": run["spider_name"],
                "spider_id": run["run_id"],
                "status": run["status"],
                "restart_count": 0,
                "pid": None,
            }
            for run in self._active_runs.values()
        ]
        payload = json.dumps(
            {
                "updated_at": time.time(),
                "processes": processes,
                "runs": self._finished_runs[-100:],
            },
            ensure_ascii=False,
        )
        await self._redis.set(RUNTIME_STATUS_KEY, payload, ex=30)

    async def _sync_schedules(self) -> None:
        tasks = await self._task_store.get_all()
        existing_ids = set()

        for task in tasks:
            existing_ids.add(task.task_id)
            signature = (
                task.schedule_type,
                task.schedule_expr,
                task.enabled,
                tuple(task.spider_args),
            )
            previous = self._schedule_cache.get(task.task_id)

            if not task.enabled:
                if previous is not None:
                    await self._remove_schedule(task.task_id)
                    self._schedule_cache.pop(task.task_id, None)
                continue

            if previous != signature:
                await self._upsert_schedule(task)
                self._schedule_cache[task.task_id] = signature

        for task_id in list(self._schedule_cache):
            if task_id not in existing_ids:
                await self._remove_schedule(task_id)
                self._schedule_cache.pop(task_id, None)

    async def _upsert_schedule(self, task: SpiderTask) -> None:
        if not self._scheduler:
            return
        await self._remove_schedule(task.task_id)

        if task.schedule_type == "cron":
            trigger = CronTrigger.from_crontab(task.schedule_expr)
        else:
            trigger = IntervalTrigger(seconds=int(task.schedule_expr))

        await self._scheduler.add_schedule(
            self._execute_task,
            trigger,
            id=task.task_id,
            args=[task.task_id],
        )

    async def _remove_schedule(self, task_id: str) -> None:
        if not self._scheduler:
            return
        try:
            result = self._scheduler.remove_schedule(task_id)
            if inspect.isawaitable(result):
                await result
        except Exception:
            # 任务可能尚未注册，忽略
            pass

    async def _handle_command(self, command: dict) -> None:
        command_id = str(command.get("command_id", "")).strip()
        action = command.get("command")
        task_id = command.get("task_id")
        if not action or not task_id:
            return

        if action not in SUPPORTED_COMMANDS:
            if command_id:
                await self._set_command_status(
                    command_id, str(action), str(task_id), "fail",
                    "unsupported command",
                )
            logger.warning("收到未知命令: command=%s, task_id=%s", action, task_id)
            return

        if command_id:
            first_seen = await self._redis.set(
                PROCESSED_COMMAND_KEY.format(command_id=command_id),
                "1",
                ex=self._command_dedupe_ttl_seconds,
                nx=True,
            )
            if not first_seen:
                logger.info("忽略重复命令: command_id=%s", command_id)
                return

        if command_id:
            await self._set_command_status(
                command_id, action, task_id, "running",
            )

        task = await self._task_store.get(task_id)
        if not task:
            if command_id:
                await self._set_command_status(
                    command_id, action, task_id, "fail", "task not found",
                )
            return

        try:
            if action == "run_task":
                await self._execute_task(task_id)
            elif action == "stop_task":
                task.enabled = False
                await self._task_store.save(task)
                logger.info(
                    "stop_task 已执行: task_id=%s, enabled=false",
                    task_id,
                )
            if command_id:
                await self._set_command_status(
                    command_id, action, task_id, "success",
                )
        except Exception as e:
            if command_id:
                await self._set_command_status(
                    command_id, action, task_id, "fail", str(e),
                )
            raise

    async def _execute_task(self, task_id: str) -> None:
        task = await self._task_store.get(task_id)
        if not task:
            return

        run_id = f"{task.spider_name}_{uuid.uuid4().hex[:8]}"
        run = {
            "run_id": run_id,
            "task_id": task.task_id,
            "spider_name": task.spider_name,
            "status": "running",
            "started_at": time.time(),
            "ended_at": None,
            "added": 0,
            "duplicated": 0,
            "source": "scheduler",
        }
        self._active_runs[run_id] = run
        await self._publish_runtime_status()

        try:
            result = await self._enqueue_task_seeds(task)
            task.last_run = time.time()
            await self._task_store.save(task)

            run["status"] = "success"
            run["ended_at"] = time.time()
            run["added"] = result["added"]
            run["duplicated"] = result["duplicated"]
            self._finished_runs.append(run.copy())
            # 限制历史记录，防止内存泄漏
            self._finished_runs = self._finished_runs[-1000:]
            self._active_runs.pop(run_id, None)
            await self._publish_runtime_status()

            SCHEDULER_TASK_EXECUTIONS.labels(
                spider_name=task.spider_name, result="success",
            ).inc()
        except Exception:
            run["status"] = "fail"
            run["ended_at"] = time.time()
            self._finished_runs.append(run.copy())
            # 限制历史记录，防止内存泄漏
            self._finished_runs = self._finished_runs[-1000:]
            self._active_runs.pop(run_id, None)
            await self._publish_runtime_status()

            SCHEDULER_TASK_EXECUTIONS.labels(
                spider_name=task.spider_name, result="fail",
            ).inc()
            logger.exception("任务执行失败: task_id=%s", task_id)

    async def _enqueue_task_seeds(self, task: SpiderTask) -> dict[str, int]:
        """将任务输入转换为种子并注入 Redis 队列。

        约定：
        - spider_args 中以 http:// 或 https:// 开头的参数视为种子 URL。
        - 若无 URL 参数，则视为任务配置错误并抛出异常。
        """
        urls = extract_seed_urls(task.spider_args)
        if not urls:
            raise ValueError(
                "task.spider_args 必须包含至少一个 URL (http/https)"
            )

        injector = SeedInjector(self._redis, task.spider_name)
        await injector.init()

        seeds = [
            SeedMeta(
                url=url,
                spider_name=task.spider_name,
                priority=5.0,
                seed_type="once",
            )
            for url in urls
        ]
        result = await injector.inject_batch(seeds)
        logger.info(
            "任务已注入种子: task_id=%s, spider=%s, added=%d, duplicated=%d",
            task.task_id, task.spider_name, result["added"], result["duplicated"],
        )
        return result

    async def _set_command_status(
        self,
        command_id: str,
        command: str,
        task_id: str,
        status: str,
        error: str = "",
    ) -> None:
        await self._redis.set(
            COMMAND_STATUS_KEY.format(command_id=command_id),
            json.dumps(
                {
                    "command_id": command_id,
                    "command": command,
                    "task_id": task_id,
                    "status": status,
                    "error": error,
                    "updated_at": time.time(),
                },
                ensure_ascii=False,
            ),
            ex=self._command_status_ttl_seconds,
        )


async def _run_standalone() -> None:
    """独立进程运行调度器（带 Redis leader 锁）。"""
    import signal

    from src.config import get_settings
    from src.infra.connections import ConnectionManager
    from src.logger.intercept import intercept_stdlib_logging

    intercept_stdlib_logging()
    settings = get_settings()
    settings.validate_runtime_safety(service="scheduler")
    conn = ConnectionManager(settings)
    await conn.startup()

    stop_event = asyncio.Event()

    def _handle_signal():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    node_id = os.getenv("HOSTNAME", f"node-{uuid.uuid4().hex[:6]}")
    logger.info("调度器进程启动: node_id=%s", node_id)

    scheduler: SpiderScheduler | None = None
    while not stop_event.is_set():
        acquired, lock, extend_task = await acquire_scheduler_lock(
            conn.redis, node_id,
        )
        if not acquired:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            continue

        scheduler = SpiderScheduler(
            conn.redis,
            command_status_ttl_seconds=settings.scheduler_command_status_ttl_seconds,
            command_dedupe_ttl_seconds=settings.scheduler_command_dedupe_ttl_seconds,
        )
        await scheduler.start()
        logger.info("当前节点成为 leader，开始调度")

        wait_tasks = [asyncio.create_task(stop_event.wait())]
        if extend_task:
            wait_tasks.append(extend_task)

        done, pending = await asyncio.wait(
            wait_tasks, return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        if scheduler:
            await scheduler.stop()
            scheduler = None
        await release_scheduler_lock(lock, extend_task)

        if not stop_event.is_set():
            logger.warning("leader 锁已释放，准备重新竞争")

    await conn.shutdown()
    logger.info("调度器独立进程已退出")


if __name__ == "__main__":
    asyncio.run(_run_standalone())
