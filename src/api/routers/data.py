"""数据查询路由

接入 PostgreSQL，提供安全的参数化结构化查询。
"""

from __future__ import annotations

import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg.sql import SQL, Identifier, Placeholder

from src.api.auth import require_roles
from src.api.deps import get_conn

router = APIRouter(prefix="/data", tags=["data"])

ALLOWED_TABLES = {"spider_results", "spider_logs", "spider_tasks"}

# 每张表允许的过滤字段白名单
ALLOWED_COLUMNS = {
    "spider_results": {
        "spider_name", "spider_id", "trace_id", "url", "created_at",
    },
    "spider_logs": {
        "spider_name", "spider_id", "trace_id", "level", "message",
        "module", "timestamp",
    },
    "spider_tasks": {
        "task_id", "spider_name", "schedule_type", "enabled", "status",
    },
}


class DataQuery(BaseModel):
    table: str
    filters: dict[str, Any] = {}
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = Field(default=20, le=100)


_TIME_COLUMN_MAP = {
    "spider_logs": "timestamp",
    "spider_results": "created_at",
    "spider_tasks": "created_at",
}


def _parse_time_filter(value: Any) -> datetime.datetime:
    """解析时间筛选值，支持 epoch 毫秒/秒与 ISO 时间字符串。"""
    if isinstance(value, (int, float)):
        ts = float(value)
        # 前端 date picker 默认是毫秒时间戳
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    if isinstance(value, str):
        # 兼容 ISO 字符串
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    raise HTTPException(400, "invalid time filter format")


def _escape_like(val: str) -> str:
    """转义 LIKE 通配符，防止用户构造恶意模式"""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post("/query")
async def query_data(
    q: DataQuery,
    user: dict = Depends(require_roles("admin", "operator")),
):
    """结构化数据查询（参数化，防注入）"""
    if q.table not in ALLOWED_TABLES:
        raise HTTPException(400, "Table not allowed")

    allowed_cols = ALLOWED_COLUMNS[q.table]
    conn = get_conn()

    # 构建 WHERE 子句
    conditions = []
    params: list[Any] = []
    for col, val in q.filters.items():
        if col not in allowed_cols:
            continue
        # message 字段用 LIKE 模糊匹配，转义通配符
        if col == "message":
            conditions.append(SQL("{} ILIKE {}").format(Identifier(col), Placeholder()))
            params.append(f"%{_escape_like(str(val))}%")
        else:
            conditions.append(SQL("{} = {}").format(Identifier(col), Placeholder()))
            params.append(val)

    # 时间范围筛选（前端使用 time_start/time_end）
    time_col = _TIME_COLUMN_MAP.get(q.table)
    if time_col:
        if "time_start" in q.filters:
            dt = _parse_time_filter(q.filters["time_start"])
            conditions.append(
                SQL("{} >= {}").format(Identifier(time_col), Placeholder())
            )
            params.append(dt)
        if "time_end" in q.filters:
            dt = _parse_time_filter(q.filters["time_end"])
            conditions.append(
                SQL("{} <= {}").format(Identifier(time_col), Placeholder())
            )
            params.append(dt)

    where = SQL("")
    if conditions:
        where = SQL(" WHERE ") + SQL(" AND ").join(conditions)

    # 排序
    order = SQL("")
    if q.sort_by and q.sort_by in allowed_cols:
        # 验证排序方向，防止 SQL 注入
        if q.sort_order.lower() not in {"asc", "desc"}:
            raise HTTPException(400, "Invalid sort order")
        direction = SQL("DESC") if q.sort_order.lower() == "desc" else SQL("ASC")
        order = SQL(" ORDER BY {} ").format(Identifier(q.sort_by)) + direction

    # 分页
    offset = (q.page - 1) * q.page_size
    limit_clause = SQL(" LIMIT {} OFFSET {}").format(
        Placeholder(), Placeholder(),
    )
    params_data = params + [q.page_size, offset]

    # 执行查询
    base = SQL("SELECT * FROM {}").format(Identifier(q.table))
    query_sql = base + where + order + limit_clause

    count_sql = SQL("SELECT COUNT(*) FROM {}").format(Identifier(q.table)) + where

    async with conn.pg.connection() as c:
        # 总数
        row = await c.execute(count_sql, params)
        total = (await row.fetchone())[0]

        # 数据
        cur = await c.execute(query_sql, params_data)
        columns = [desc.name for desc in cur.description]
        rows = await cur.fetchall()

    data = [dict(zip(columns, r)) for r in rows]
    return {"data": data, "total": total, "page": q.page}
