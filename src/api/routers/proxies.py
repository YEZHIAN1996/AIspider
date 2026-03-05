"""代理池路由

接入 proxy 模块，提供代理池状态查询和刷新。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.auth import require_roles
from src.api.deps import get_conn, get_proxy_pool

router = APIRouter(prefix="/proxies", tags=["proxies"])

_BAD_KEY = "proxy:bad"


@router.get("/")
async def get_proxy_status(user: dict = Depends(require_roles("admin", "operator"))):
    """获取代理池状态"""
    pool = get_proxy_pool()
    conn = get_conn()
    pool_size = await pool.size()
    bad_count = await conn.redis.scard(_BAD_KEY)
    return {"pool_size": pool_size, "bad_count": bad_count}


@router.post("/refresh")
async def refresh_proxies(user: dict = Depends(require_roles("admin"))):
    """刷新代理池（清理过期代理，触发重新拉取）"""
    conn = get_conn()
    # 清理 bad 池
    await conn.redis.delete(_BAD_KEY)
    pool = get_proxy_pool()
    pool_size = await pool.size()
    return {"msg": "refreshed", "pool_size": pool_size}
