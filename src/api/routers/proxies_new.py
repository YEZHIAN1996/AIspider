"""代理池管理 API 路由"""
from fastapi import APIRouter, Depends
from src.api.deps import get_redis, require_role
from src.proxy.pandas_provider import PandasProxyProvider
from src.config import get_settings

router = APIRouter(prefix="/proxies", tags=["proxies"])


@router.get("/")
async def get_proxy_status(redis=Depends(get_redis), _=Depends(require_role(["admin", "operator"]))):
    """获取代理池状态"""
    settings = get_settings()
    total = await redis.zcard(settings.pandas_proxy_redis_key)
    return {
        "total": total,
        "pool_size": settings.pandas_proxy_pool_size,
        "redis_key": settings.pandas_proxy_redis_key
    }


@router.post("/refresh")
async def refresh_proxies(redis=Depends(get_redis), _=Depends(require_role(["admin"]))):
    """手动触发代理刷新"""
    await redis.publish("proxy:refresh", "1")
    return {"message": "刷新请求已发送"}
