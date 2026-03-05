"""脏数据隔离处理

校验失败的数据写入 PostgreSQL 隔离表，
支持后续通过 API 查看、修正、重新入库。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# 隔离表建表 SQL
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS spider_quarantine (
    id          BIGSERIAL PRIMARY KEY,
    spider_name TEXT NOT NULL,
    trace_id    TEXT,
    raw_data    JSONB NOT NULL,
    errors      JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_quarantine_spider
    ON spider_quarantine (spider_name, status);
"""


class QuarantineStore:
    """脏数据隔离存储

    将校验失败的 item 写入 PG 隔离表，
    支持按 spider_name 查询和状态管理。
    """

    def __init__(self, pg_pool: AsyncConnectionPool) -> None:
        self._pool = pg_pool

    async def ensure_table(self) -> None:
        """确保隔离表存在（开发环境自动建表）"""
        async with self._pool.connection() as conn:
            await conn.execute(_CREATE_TABLE_SQL)
            await conn.commit()
        logger.info("隔离表 spider_quarantine 已就绪")

    async def store(
        self,
        spider_name: str,
        item: dict,
        errors: list[str],
        trace_id: str | None = None,
    ) -> None:
        """将校验失败的 item 写入隔离表"""
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO spider_quarantine
                    (spider_name, trace_id, raw_data, errors, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    spider_name,
                    trace_id,
                    json.dumps(item, ensure_ascii=False),
                    json.dumps(errors, ensure_ascii=False),
                    datetime.now(timezone.utc),
                ),
            )
            await conn.commit()

    async def query(
        self,
        spider_name: str | None = None,
        status: str = "pending",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """查询隔离数据"""
        conditions = ["status = %s"]
        params: list[object] = [status]

        if spider_name:
            conditions.append("spider_name = %s")
            params.append(spider_name)

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        async with self._pool.connection() as conn:
            cur = await conn.execute(
                f"""
                SELECT id, spider_name, trace_id, raw_data,
                       errors, status, created_at
                FROM spider_quarantine
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            rows = await cur.fetchall()

        return [
            {
                "id": r[0],
                "spider_name": r[1],
                "trace_id": r[2],
                "raw_data": r[3],
                "errors": r[4],
                "status": r[5],
                "created_at": r[6],
            }
            for r in rows
        ]

    async def resolve(self, record_id: int, new_status: str = "resolved") -> None:
        """标记隔离记录为已处理"""
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                UPDATE spider_quarantine
                SET status = %s, resolved_at = %s
                WHERE id = %s
                """,
                (new_status, datetime.now(timezone.utc), record_id),
            )
            await conn.commit()
