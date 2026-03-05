"""代理池自动补充服务"""
import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from loguru import logger
from redis.asyncio import Redis

from src.config import get_settings


class PandasProxyRefiller:
    """后台定时补充代理池"""

    def __init__(
        self,
        order_id: str,
        api_secret: str,
        redis: Redis,
        redis_key: str = "pandas_proxy",
        pool_size: int = 150,
    ):
        self.order_id = order_id
        self.api_secret = api_secret
        self.redis = redis
        self.redis_key = redis_key
        self.pool_size = pool_size
        self.api_url = "http://www.xiongmaodaili.com/xiongmao-web/apiPlus/vgb"
        self._tz_shanghai = ZoneInfo("Asia/Shanghai")

    async def _fetch_proxy_batch(
        self, client: httpx.AsyncClient, count: int,
    ) -> list[dict]:
        """调用熊猫代理 API 获取一批代理。"""
        resp = await client.get(
            self.api_url,
            params={
                "secret": self.api_secret,
                "orderNo": self.order_id,
                "count": count,
                "isTxt": 0,
                "proxyType": 1,
                "validTime": 1,
                "removal": 0,
                "returnAccount": 1,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("msg") != "ok":
            logger.warning(
                "熊猫代理接口返回非 ok: msg={}",
                payload.get("msg", ""),
            )
            return []
        data = payload.get("obj", [])
        return data if isinstance(data, list) else []

    async def refill(self, client: httpx.AsyncClient):
        """补充代理"""
        current = await self.redis.zcard(self.redis_key)
        if current >= self.pool_size:
            return

        need = min(self.pool_size - current, 10)
        try:
            batch = await self._fetch_proxy_batch(client, need)
            added = 0
            for item in batch:
                ip = item.get("ip")
                port = item.get("port")
                valid_time = item.get("validTime")
                if not ip or not port or not valid_time:
                    continue
                proxy = f"{ip}:{port}"
                dt = datetime.strptime(
                    valid_time, "%Y-%m-%d %H:%M:%S",
                ).replace(tzinfo=self._tz_shanghai)
                expire_ts = int(dt.timestamp()) - 10
                await self.redis.zadd(self.redis_key, {proxy: expire_ts})
                added += 1
            if added:
                logger.info(
                    "补充 {} 个代理到池中，当前总数: {}",
                    added, await self.redis.zcard(self.redis_key),
                )
        except Exception as e:
            logger.error("补充代理失败: {}", e)

    async def clean_expired(self):
        """清理过期代理"""
        removed = await self.redis.zremrangebyscore(self.redis_key, 0, int(time.time()))
        if removed:
            logger.info("清理 {} 个过期代理", removed)

    async def run(self):
        """运行补充循环"""
        logger.info(
            "代理池补充服务启动，订单ID: {}，目标池大小: {}",
            self.order_id, self.pool_size,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                try:
                    await self.clean_expired()
                    await self.refill(client)
                except Exception as e:
                    logger.error("代理池维护异常: {}", e)
                await asyncio.sleep(60)


async def main():
    """入口函数"""
    settings = get_settings()
    settings.validate_runtime_safety(service="proxy-refiller")
    if not settings.pandas_proxy_order_id:
        logger.error("未配置 AISPIDER_PANDAS_PROXY_ORDER_ID，退出")
        return
    if not settings.pandas_proxy_secret:
        logger.error("未配置 AISPIDER_PANDAS_PROXY_SECRET，退出")
        return

    redis = Redis.from_url(settings.redis_url)

    refiller = PandasProxyRefiller(
        order_id=settings.pandas_proxy_order_id,
        api_secret=settings.pandas_proxy_secret,
        redis=redis,
        redis_key=settings.pandas_proxy_redis_key,
        pool_size=settings.pandas_proxy_pool_size,
    )

    try:
        await refiller.run()
    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
