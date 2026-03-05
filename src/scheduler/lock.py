"""Redis 分布式锁

多节点部署时，仅 leader 节点执行调度，
通过 Redis 锁实现选主 + 后台续期。
续期任务可通过返回的 task 引用取消。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.lock import Lock

logger = logging.getLogger(__name__)


async def acquire_scheduler_lock(
    redis: Redis, node_id: str,
) -> tuple[bool, Lock, asyncio.Task | None]:
    """尝试获取调度器 leader 锁

    Returns:
        (是否获取成功, 锁对象, 续期任务引用)
    """
    from redis.asyncio.lock import Lock as RedisLock

    lock = RedisLock(
        redis,
        name="scheduler:leader",
        timeout=30,
        blocking_timeout=5,
        thread_local=False,  # 异步环境必须关闭
    )
    acquired = await lock.acquire()
    extend_task = None
    if acquired:
        logger.info("节点 %s 获取 leader 锁", node_id)
        extend_task = asyncio.create_task(_extend_lock(lock, node_id))
    return acquired, lock, extend_task


async def release_scheduler_lock(
    lock: Lock, extend_task: asyncio.Task | None,
) -> None:
    """释放锁并取消续期任务"""
    if extend_task and not extend_task.done():
        extend_task.cancel()
        try:
            await extend_task
        except asyncio.CancelledError:
            pass
    try:
        await lock.release()
    except Exception:
        logger.warning("释放 leader 锁失败（可能已过期）")


async def _extend_lock(lock: Lock, node_id: str) -> None:
    """后台续期，防止长任务期间锁过期"""
    while True:
        await asyncio.sleep(10)
        try:
            await lock.extend(30)
        except Exception:
            logger.warning("节点 %s leader 锁续期失败", node_id)
            break
