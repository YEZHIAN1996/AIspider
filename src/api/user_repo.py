"""用户存储与认证辅助。

包含：
- spider_users 表初始化
- bootstrap admin 初始化
- 密码哈希与校验
"""

from __future__ import annotations

import asyncio
import logging

import bcrypt
from psycopg import errors as pg_errors

from src.config import get_settings

logger = logging.getLogger(__name__)

_READY = False
_READY_LOCK = asyncio.Lock()


def hash_password(password: str, rounds: int) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError, AttributeError):
        return False


async def ensure_user_schema(conn) -> None:
    """确保用户表可用并按需初始化 bootstrap 管理员。

    注意：表结构由 Alembic 迁移负责；本函数不做 DDL。
    """
    global _READY
    if _READY:
        return

    async with _READY_LOCK:
        if _READY:
            return

        settings = get_settings()
        async with conn.pg.connection() as c:
            try:
                row = await (await c.execute(
                    "SELECT COUNT(*) FROM spider_users"
                )).fetchone()
            except pg_errors.UndefinedTable as exc:
                await c.rollback()
                raise RuntimeError(
                    "spider_users table not found, run `alembic upgrade head`"
                ) from exc
            total_users = row[0] if row else 0

            if total_users == 0:
                username = settings.bootstrap_admin_username
                password = settings.bootstrap_admin_password
                if username and password:
                    hashed = hash_password(password, settings.auth_bcrypt_rounds)
                    await c.execute(
                        """
                        INSERT INTO spider_users (username, password_hash, role)
                        VALUES (%s, %s, 'admin')
                        ON CONFLICT (username) DO NOTHING
                        """,
                        (username, hashed),
                    )
                    logger.warning("已创建 bootstrap admin 用户: %s", username)
                else:
                    logger.warning(
                        "当前无用户且未配置 AISPIDER_BOOTSTRAP_ADMIN_USERNAME/PASSWORD"
                    )

            await c.commit()

        _READY = True
