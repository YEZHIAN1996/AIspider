"""URL 去重模块

分层去重策略：
- 第一层：Redis Bloom Filter（低内存，允许极低误判）
- 第二层：Redis SET 精确去重（关键种子）
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Lua 脚本路径
_LUA_DIR = Path(__file__).parent / "lua"


class Deduplicator:
    """URL 去重器，封装 Bloom Filter + Lua 原子操作"""

    def __init__(self, redis: Redis, spider_name: str) -> None:
        self._redis = redis
        self._spider_name = spider_name
        self._bloom_key = f"bf:{spider_name}"
        self._script_sha: str | None = None

    @staticmethod
    def fingerprint(url: str) -> str:
        """生成 URL 指纹"""
        return hashlib.sha1(url.encode()).hexdigest()

    async def init_bloom(
        self,
        capacity: int = 10_000_000,
        error_rate: float = 0.001,
    ) -> None:
        """初始化 Bloom Filter（如果不存在）"""
        try:
            await self._redis.execute_command(
                "BF.RESERVE", self._bloom_key,
                error_rate, capacity, "NONSCALING",
            )
            logger.info(
                "Bloom Filter 已创建: %s (容量=%d, 误判率=%s)",
                self._bloom_key, capacity, error_rate,
            )
        except Exception as e:
            if "item exists" in str(e).lower():
                logger.debug("Bloom Filter 已存在: %s", self._bloom_key)
            else:
                raise

    async def _load_script(self) -> str:
        """加载并缓存 Lua 脚本"""
        if self._script_sha is None:
            lua_path = _LUA_DIR / "check_and_add.lua"
            script = lua_path.read_text()
            self._script_sha = await self._redis.script_load(script)
        return self._script_sha

    async def exists(self, url: str) -> bool:
        """检查 URL 是否已存在"""
        fp = self.fingerprint(url)
        result = await self._redis.execute_command(
            "BF.EXISTS", self._bloom_key, fp,
        )
        return bool(result)

    async def check_and_add(
        self,
        url: str,
        priority: float,
        seed_json: str,
        queue_key: str,
        ttl: int = 0,
    ) -> bool:
        """原子操作：去重检查 + 入队

        Returns:
            True = 新增成功, False = 已存在
        """
        sha = await self._load_script()
        fp = self.fingerprint(url)
        result = await self._redis.evalsha(
            sha, 2,
            self._bloom_key, queue_key,
            fp, priority, seed_json, ttl,
        )
        return bool(result)
