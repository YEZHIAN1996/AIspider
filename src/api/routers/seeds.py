"""种子管理路由

接入 seed 模块，提供队列状态查询、种子注入、批量导入。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.auth import require_roles
from src.api.deps import get_conn
from src.seed.injector import SeedInjector, SeedMeta
from src.seed.queue import SeedQueue

router = APIRouter(prefix="/seeds", tags=["seeds"])


class SeedImportItem(BaseModel):
    url: str
    spider_name: str
    priority: float = 5.0
    seed_type: str = "once"
    max_retry: int = 3
    ttl: int = 86400


class SeedImportRequest(BaseModel):
    seeds: list[SeedImportItem] = []
    # 兼容单条添加
    url: str | None = None
    spider_name: str | None = None
    priority: float = 5.0


@router.get("/")
async def get_seed_status(user: dict = Depends(require_roles("admin", "operator"))):
    """获取所有 spider 的种子队列状态"""
    conn = get_conn()
    redis = conn.redis
    queues = []
    total = 0
    cursor = "0"
    while True:
        cursor, keys = await redis.scan(cursor, match="queue:*", count=100)
        for key in keys:
            spider_name = key.replace("queue:", "")
            sq = SeedQueue(redis, spider_name)
            size = await sq.size()
            top = await redis.zrevrange(key, 0, 0, withscores=True)
            bottom = await redis.zrange(key, 0, 0, withscores=True)
            hi = top[0][1] if top else 0
            lo = bottom[0][1] if bottom else 0
            queues.append({
                "spider_name": spider_name,
                "size": size,
                "priority_range": [lo, hi],
            })
            total += size
        if cursor == "0":
            break
    return {"queues": queues, "total": total}


@router.post("/import")
async def import_seeds(
    req: SeedImportRequest,
    user: dict = Depends(require_roles("admin")),
):
    """批量导入种子"""
    conn = get_conn()
    redis = conn.redis

    # 构建种子列表：支持批量和单条两种模式
    items: list[SeedImportItem] = list(req.seeds)
    if req.url and req.spider_name:
        items.append(SeedImportItem(
            url=req.url,
            spider_name=req.spider_name,
            priority=req.priority,
        ))

    if not items:
        raise HTTPException(400, "No seeds provided")

    # 按 spider_name 分组注入
    results = {"added": 0, "duplicated": 0}
    grouped: dict[str, list[SeedImportItem]] = {}
    for item in items:
        grouped.setdefault(item.spider_name, []).append(item)

    for spider_name, group in grouped.items():
        injector = SeedInjector(redis, spider_name)
        await injector.init()
        seed_metas = [
            SeedMeta(
                url=s.url,
                spider_name=s.spider_name,
                priority=s.priority,
                seed_type=s.seed_type,
                max_retry=s.max_retry,
                ttl=s.ttl,
            )
            for s in group
        ]
        r = await injector.inject_batch(seed_metas)
        results["added"] += r["added"]
        results["duplicated"] += r["duplicated"]

    return {
        "msg": "imported",
        "count": results["added"],
        "duplicated": results["duplicated"],
    }
