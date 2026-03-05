"""全局连接管理器

统一管理 Redis / PostgreSQL / Kafka / MinIO 的连接池，
应用启动时调用 startup()，关闭时调用 shutdown()。
Kafka 连接支持重试，适应容器编排中的启动顺序不确定性。
"""

from __future__ import annotations

import asyncio
import logging

from aiokafka import AIOKafkaProducer
from miniopy_async import Minio
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from src.config import Settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """全局连接管理器，每个进程持有一个实例"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pg_pool: AsyncConnectionPool | None = None
        self._redis: Redis | None = None
        self._kafka_producer: AIOKafkaProducer | None = None
        self._minio: Minio | None = None
        self._started = False

    # ---- 生命周期 ----

    async def startup(self) -> None:
        """初始化所有连接，应用启动时调用"""
        if self._started:
            return

        logger.info("ConnectionManager: 正在初始化连接...")

        try:
            # PostgreSQL 连接池
            self._pg_pool = AsyncConnectionPool(
                conninfo=self._settings.pg_dsn,
                min_size=self._settings.pg_pool_min,
                max_size=self._settings.pg_pool_max,
                open=False,
            )
            await self._pg_pool.open()

            # Redis
            self._redis = Redis.from_url(
                self._settings.redis_url,
                decode_responses=True,
            )

            # MinIO
            self._minio = Minio(
                self._settings.minio_endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_secure,
            )

            # Kafka Producer（带重试，适应容器启动顺序）
            self._kafka_producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.kafka_brokers,
            )
            for attempt in range(1, 11):
                try:
                    await self._kafka_producer.start()
                    break
                except Exception as e:
                    if attempt == 10:
                        await self._cleanup_partial()
                        raise
                    logger.warning(
                        "Kafka 连接失败，%d秒后重试 (%d/10): %s",
                        attempt * 3, attempt, e,
                    )
                    await asyncio.sleep(attempt * 3)

            self._started = True
            logger.info("ConnectionManager: 所有连接已就绪")
        except Exception:
            await self._cleanup_partial()
            raise

    async def _cleanup_partial(self) -> None:
        """清理部分初始化的资源"""
        if self._kafka_producer:
            try:
                await self._kafka_producer.stop()
            except Exception:
                pass
            self._kafka_producer = None

        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None

        if self._pg_pool:
            try:
                await self._pg_pool.close()
            except Exception:
                pass
            self._pg_pool = None

        self._minio = None

    async def shutdown(self) -> None:
        """关闭所有连接，应用退出时调用"""
        if not self._started:
            return

        logger.info("ConnectionManager: 正在关闭连接...")

        if self._kafka_producer:
            await self._kafka_producer.stop()
            self._kafka_producer = None

        if self._redis:
            await self._redis.close()
            self._redis = None

        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None

        self._minio = None
        self._started = False
        logger.info("ConnectionManager: 所有连接已关闭")

    # ---- 属性访问 ----

    @property
    def pg(self) -> AsyncConnectionPool:
        assert self._pg_pool is not None, "ConnectionManager 未启动"
        return self._pg_pool

    @property
    def redis(self) -> Redis:
        assert self._redis is not None, "ConnectionManager 未启动"
        return self._redis

    @property
    def kafka(self) -> AIOKafkaProducer:
        assert self._kafka_producer is not None, "ConnectionManager 未启动"
        return self._kafka_producer

    @property
    def minio(self) -> Minio:
        assert self._minio is not None, "ConnectionManager 未启动"
        return self._minio

    @property
    def is_started(self) -> bool:
        return self._started
