"""FastAPI 依赖注入

提供全局连接管理器、任务服务、代理池等单例依赖。
"""

from __future__ import annotations

from src.config import get_settings
from src.infra.connections import ConnectionManager
from src.proxy.pool import RedisProxyPool
from src.scheduler.service import TaskService

_conn_manager: ConnectionManager | None = None
_proxy_pool: RedisProxyPool | None = None
_task_service: TaskService | None = None


def get_conn() -> ConnectionManager:
    """获取全局连接管理器"""
    global _conn_manager
    if _conn_manager is None:
        _conn_manager = ConnectionManager(get_settings())
    return _conn_manager


def get_proxy_pool() -> RedisProxyPool:
    """获取全局代理池"""
    global _proxy_pool
    if _proxy_pool is None:
        conn = get_conn()
        _proxy_pool = RedisProxyPool(conn.redis)
    return _proxy_pool


def get_task_service() -> TaskService:
    """获取任务服务（API 通过 Redis 与 scheduler 解耦）"""
    global _task_service
    if _task_service is None:
        conn = get_conn()
        _task_service = TaskService(conn.redis)
    return _task_service
