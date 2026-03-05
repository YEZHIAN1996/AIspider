"""本地文件监听（开发环境）

单机开发/测试环境下，通过监听日志文件变化触发告警，
生产环境应使用 Kafka 消费方式。
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class LogFileWatchdog:
    """本地日志文件监听器

    定时轮询错误日志文件，发现新内容时触发告警。
    仅用于开发/测试环境。

    Args:
        log_dir: 日志目录
        notifiers: 通知渠道列表
        poll_interval: 轮询间隔（秒）
    """

    def __init__(
        self,
        log_dir: str,
        notifiers: list,
        poll_interval: float = 10.0,
    ) -> None:
        self._log_dir = log_dir
        self._notifiers = notifiers
        self._poll_interval = poll_interval
        self._offsets: dict[str, int] = {}
        self._running = False

    async def start(self) -> None:
        """启动轮询"""
        self._running = True
        logger.info("LogFileWatchdog 已启动: %s", self._log_dir)
        while self._running:
            await self._poll()
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        """停止轮询"""
        self._running = False

    async def _poll(self) -> None:
        """轮询错误日志文件"""
        if not os.path.isdir(self._log_dir):
            return

        for fname in os.listdir(self._log_dir):
            if not fname.endswith("_error.log"):
                continue
            fpath = os.path.join(self._log_dir, fname)
            size = os.path.getsize(fpath)
            prev = self._offsets.get(fpath, size)

            if size <= prev:
                self._offsets[fpath] = size
                continue

            # 读取新增内容
            with open(fpath, encoding="utf-8", errors="replace") as f:
                f.seek(prev)
                new_lines = f.read(4096)
            self._offsets[fpath] = size

            if new_lines.strip():
                for notifier in self._notifiers:
                    try:
                        await notifier.send(
                            f"[Watchdog] {fname}\n{new_lines[:500]}"
                        )
                    except Exception:
                        logger.exception("Watchdog 告警发送失败")
