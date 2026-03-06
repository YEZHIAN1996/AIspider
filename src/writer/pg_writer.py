"""PostgreSQL 批量写入模块

使用 psycopg 3 参数化查询防止 SQL 注入，
支持批量 INSERT 和 COPY 协议高性能写入。
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

from psycopg.sql import SQL, Identifier, Placeholder

from src.infra.metrics import (
    WRITE_FAIL_TOTAL,
    WRITE_LATENCY,
    WRITE_SUCCESS_TOTAL,
)

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# SQL 标识符白名单正则（仅允许字母、数字、下划线）
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_identifier(name: str) -> None:
    """验证 SQL 标识符（表名、列名）安全性"""
    if not _IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Invalid SQL identifier: {name}")


def build_batch_insert(table: str, columns: list[str]) -> SQL:
    """构建安全的批量插入 SQL（参数化查询防止注入）"""
    validate_identifier(table)
    for col in columns:
        validate_identifier(col)

    return SQL(
        "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING"
    ).format(
        Identifier(table),
        SQL(", ").join(map(Identifier, columns)),
        SQL(", ").join(Placeholder() * len(columns)),
    )


class PgWriter:
    """PostgreSQL 批量写入器

    Args:
        pool: psycopg AsyncConnectionPool 实例
        table: 目标表名
        columns: 写入列名列表
    """

    def __init__(
        self,
        pool: AsyncConnectionPool,
        table: str,
        columns: list[str],
    ) -> None:
        self._pool = pool
        self._table = table
        self._columns = columns
        self._query = build_batch_insert(table, columns)

    async def write_batch(self, rows: list[dict]) -> int:
        """批量写入数据

        Args:
            rows: 数据字典列表

        Returns:
            成功写入的行数
        """
        if not rows:
            return 0

        values = [
            [row.get(col) for col in self._columns]
            for row in rows
        ]
        start = time.monotonic()

        try:
            async with self._pool.connection() as conn:
                await conn.executemany(self._query, values)
                await conn.commit()

            elapsed = time.monotonic() - start
            WRITE_SUCCESS_TOTAL.labels(target="postgres").inc(len(rows))
            WRITE_LATENCY.labels(target="postgres").observe(elapsed)
            return len(rows)

        except Exception:
            WRITE_FAIL_TOTAL.labels(target="postgres").inc(len(rows))
            logger.exception(
                "PG 批量写入失败: table=%s, batch_size=%d",
                self._table, len(rows),
            )
            raise
