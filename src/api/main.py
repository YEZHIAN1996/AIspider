"""FastAPI 网关入口

应用生命周期管理、路由注册、CORS 配置、Prometheus 指标暴露。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.api.deps import get_conn
from src.config import get_settings
from src.logger.intercept import intercept_stdlib_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化连接和调度器，关闭时清理"""
    intercept_stdlib_logging()
    conn = get_conn()
    await conn.startup()

    # 挂载 Kafka 和 Redis PubSub 日志 sink
    from src.logger.sinks import (
        attach_kafka_sink,
        attach_redis_pubsub_sink,
        start_log_workers,
        stop_log_workers,
    )
    await start_log_workers(conn.kafka, conn.redis)
    kafka_handler_id = attach_kafka_sink(conn.kafka)
    redis_handler_id = attach_redis_pubsub_sink(conn.redis)

    yield

    # 移除日志 sink
    from loguru import logger
    logger.remove(kafka_handler_id)
    logger.remove(redis_handler_id)
    await stop_log_workers()

    await conn.shutdown()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    settings = get_settings()
    settings.validate_runtime_safety(service="api")

    app = FastAPI(
        title="AIspider API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — 从统一配置读取允许的源，生产环境由配置校验禁止 *
    allowed_origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus 指标端点
    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return PlainTextResponse(
            generate_latest(), media_type=CONTENT_TYPE_LATEST,
        )

    # 注册路由
    from src.api.routers import auth, tasks, seeds, proxies, monitor, data, ws, users
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(seeds.router, prefix="/api/v1")
    app.include_router(proxies.router, prefix="/api/v1")
    app.include_router(monitor.router, prefix="/api/v1")
    app.include_router(data.router, prefix="/api/v1")
    app.include_router(ws.router)

    return app
