"""健康检查模块

统一探测 Redis / PostgreSQL / Kafka / MinIO 的可用性，
供 API 网关的 /health 端点和监控模块调用。
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infra.connections import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class ComponentStatus:
    name: str
    status: str  # ok | error
    latency_ms: float = 0.0
    detail: str = ""


@dataclass
class HealthReport:
    healthy: bool = True
    components: list[ComponentStatus] = field(default_factory=list)
    checked_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "checked_at": self.checked_at,
            "components": {
                c.name: {
                    "status": c.status,
                    "latency_ms": round(c.latency_ms, 2),
                    "detail": c.detail,
                }
                for c in self.components
            },
        }


class HealthChecker:
    """统一健康检查器"""

    def __init__(self, conn: ConnectionManager) -> None:
        self._conn = conn

    async def check_all(self) -> HealthReport:
        """并发检查所有组件"""
        report = HealthReport(checked_at=time.time())

        checks = [
            self._check_redis(),
            self._check_postgres(),
            self._check_kafka(),
            self._check_minio(),
        ]

        import asyncio
        results = await asyncio.gather(*checks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                cs = ComponentStatus(
                    name="unknown",
                    status="error",
                    detail=str(result),
                )
            else:
                cs = result
            report.components.append(cs)
            if cs.status != "ok":
                report.healthy = False

        return report

    async def _check_redis(self) -> ComponentStatus:
        name = "redis"
        start = time.monotonic()
        try:
            await self._conn.redis.ping()
            latency = (time.monotonic() - start) * 1000
            return ComponentStatus(
                name=name, status="ok", latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.warning("Redis 健康检查失败: %s", e)
            return ComponentStatus(
                name=name, status="error",
                latency_ms=latency, detail=str(e),
            )

    async def _check_postgres(self) -> ComponentStatus:
        name = "postgres"
        start = time.monotonic()
        try:
            async with self._conn.pg.connection() as conn:
                await conn.execute("SELECT 1")
            latency = (time.monotonic() - start) * 1000
            return ComponentStatus(
                name=name, status="ok", latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.warning("PostgreSQL 健康检查失败: %s", e)
            return ComponentStatus(
                name=name, status="error",
                latency_ms=latency, detail=str(e),
            )

    async def _check_kafka(self) -> ComponentStatus:
        name = "kafka"
        start = time.monotonic()
        try:
            # partitions_for 返回 None 表示 topic 不存在但连接正常
            await self._conn.kafka.partitions_for("__consumer_offsets")
            latency = (time.monotonic() - start) * 1000
            return ComponentStatus(
                name=name, status="ok", latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.warning("Kafka 健康检查失败: %s", e)
            return ComponentStatus(
                name=name, status="error",
                latency_ms=latency, detail=str(e),
            )

    async def _check_minio(self) -> ComponentStatus:
        name = "minio"
        start = time.monotonic()
        try:
            await self._conn.minio.list_buckets()
            latency = (time.monotonic() - start) * 1000
            return ComponentStatus(
                name=name, status="ok", latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.warning("MinIO 健康检查失败: %s", e)
            return ComponentStatus(
                name=name, status="error",
                latency_ms=latency, detail=str(e),
            )
