"""子进程生命周期管理

管理 Scrapy Worker 子进程的启动、停止、监控和自动重启。
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field

from src.infra.metrics import SCHEDULER_TASKS_RUNNING

logger = logging.getLogger(__name__)


@dataclass
class SpiderProcess:
    """单个爬虫子进程状态"""

    spider_name: str
    spider_id: str
    process: asyncio.subprocess.Process | None = None
    status: str = "idle"  # idle | running | stopping | failed
    restart_count: int = 0
    max_restarts: int = 3


class ProcessManager:
    """管理 Scrapy 子进程的生命周期"""

    def __init__(self) -> None:
        self._processes: dict[str, SpiderProcess] = {}

    @property
    def running_count(self) -> int:
        return sum(
            1 for sp in self._processes.values()
            if sp.status == "running"
        )

    async def start_spider(
        self,
        spider_name: str,
        spider_id: str,
        args: list[str] | None = None,
    ) -> str:
        """启动一个 Scrapy 子进程"""
        cmd = [
            "scrapy", "crawl", spider_name,
            "-s", f"SPIDER_ID={spider_id}",
            *(args or []),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 复用已有的 SpiderProcess 对象以保留 restart_count
        existing = self._processes.get(spider_id)
        if existing is not None:
            existing.process = proc
            existing.status = "running"
            sp = existing
        else:
            sp = SpiderProcess(
                spider_name=spider_name,
                spider_id=spider_id,
                process=proc,
                status="running",
            )
            self._processes[spider_id] = sp

        SCHEDULER_TASKS_RUNNING.set(self.running_count)
        asyncio.create_task(self._watch_process(sp))
        logger.info(
            "Spider 已启动: name=%s, id=%s, pid=%d",
            spider_name, spider_id, proc.pid,
        )
        return spider_id

    async def stop_spider(self, spider_id: str, timeout: float = 30) -> None:
        """优雅停止子进程"""
        sp = self._processes.get(spider_id)
        if not sp or not sp.process:
            return
        sp.status = "stopping"
        sp.process.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(sp.process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            sp.process.kill()
        sp.status = "idle"
        SCHEDULER_TASKS_RUNNING.set(self.running_count)
        logger.info("Spider 已停止: id=%s", spider_id)

    async def stop_all(self) -> None:
        """停止所有子进程"""
        ids = [
            sid for sid, sp in self._processes.items()
            if sp.status == "running"
        ]
        for sid in ids:
            await self.stop_spider(sid)

    async def _watch_process(self, sp: SpiderProcess, timeout: float = 3600) -> None:
        """监控子进程退出，异常退出时自动重启"""
        try:
            returncode = await asyncio.wait_for(sp.process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Spider 进程超时未退出，强制终止: id=%s", sp.spider_id)
            sp.process.kill()
            returncode = -1

        SCHEDULER_TASKS_RUNNING.set(self.running_count)

        if returncode != 0 and sp.status != "stopping":
            sp.status = "failed"
            if sp.restart_count < sp.max_restarts:
                sp.restart_count += 1
                logger.warning(
                    "Spider 异常退出，自动重启: id=%s, retry=%d/%d",
                    sp.spider_id, sp.restart_count, sp.max_restarts,
                )
                await self.start_spider(sp.spider_name, sp.spider_id)
            else:
                logger.error(
                    "Spider 重启次数耗尽: id=%s", sp.spider_id,
                )

    def get_status(self) -> list[dict]:
        """获取所有子进程状态"""
        return [
            {
                "spider_name": sp.spider_name,
                "spider_id": sp.spider_id,
                "status": sp.status,
                "restart_count": sp.restart_count,
                "pid": sp.process.pid if sp.process else None,
            }
            for sp in self._processes.values()
        ]
