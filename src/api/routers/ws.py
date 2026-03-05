"""WebSocket 实时路由

提供日志流、Dashboard 实时数据、告警推送三个 WebSocket 端点。
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt

from src.config import get_settings
from src.api.deps import get_conn, get_task_service

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


def _extract_ws_token(websocket: WebSocket) -> str:
    token = websocket.query_params.get("token")
    if token:
        return token

    auth = websocket.headers.get("authorization", "")
    prefix = "Bearer "
    if auth.startswith(prefix):
        return auth[len(prefix):]
    return ""


async def _authorize_ws(
    websocket: WebSocket,
    allowed_roles: tuple[str, ...] = ("admin", "operator"),
) -> dict | None:
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return None

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4401, reason="Token expired")
        return None
    except jwt.InvalidTokenError:
        await websocket.close(code=4401, reason="Invalid token")
        return None

    if allowed_roles and payload.get("role") not in allowed_roles:
        await websocket.close(code=4403, reason="Insufficient role")
        return None
    return payload


@router.websocket("/ws/logs/{spider_id}")
async def ws_logs(websocket: WebSocket, spider_id: str):
    """实时推送指定 spider 的日志（从 Redis PubSub 订阅）"""
    payload = await _authorize_ws(websocket, allowed_roles=("admin", "operator"))
    if payload is None:
        return
    await websocket.accept()
    conn = get_conn()
    pubsub = conn.redis.pubsub()
    channel = f"logs:{spider_id}"
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0,
            )
            if msg and msg["type"] == "message":
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
            else:
                # 无消息时发心跳保持连接
                await asyncio.sleep(2)
                await websocket.send_json({
                    "spider_id": spider_id,
                    "type": "heartbeat",
                })
    except WebSocketDisconnect:
        logger.info("WebSocket 断开: spider_id=%s", spider_id)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """Dashboard 实时数据推送（每 5 秒推送一次摘要）"""
    payload = await _authorize_ws(websocket, allowed_roles=("admin", "operator"))
    if payload is None:
        return
    await websocket.accept()
    conn = get_conn()
    task_service = get_task_service()
    try:
        while True:
            # 收集实时指标
            runtime = await task_service.get_runtime_status()
            procs = runtime.get("processes", [])
            running = sum(1 for p in procs if p["status"] == "running")

            # 队列积压
            queue_size = 0
            cursor = 0
            while True:
                cursor, keys = await conn.redis.scan(
                    cursor, match="queue:*", count=100,
                )
                for key in keys:
                    queue_size += await conn.redis.zcard(key)
                if cursor == 0:
                    break

            payload = {
                "type": "dashboard",
                "running_spiders": running,
                "queue_size": queue_size,
                "crawl_rate": running * 10,  # 估算值，后续接入真实指标
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket 断开")


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """告警实时推送（订阅 Redis PubSub alerts 频道）"""
    payload = await _authorize_ws(websocket, allowed_roles=("admin",))
    if payload is None:
        return
    await websocket.accept()
    conn = get_conn()
    pubsub = conn.redis.pubsub()
    await pubsub.subscribe("alerts")
    try:
        while True:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0,
            )
            if msg and msg["type"] == "message":
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
            else:
                await asyncio.sleep(2)
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        logger.info("Alerts WebSocket 断开")
    finally:
        await pubsub.unsubscribe("alerts")
        await pubsub.close()
