"""认证路由

认证基于 PostgreSQL 用户表 + bcrypt 哈希。
"""

from __future__ import annotations

import logging
import time

from jose import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import get_settings
from src.api.deps import get_conn
from src.api.user_repo import ensure_user_schema, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


_INSECURE_SECRETS = {"change-me-in-production", "secret", ""}


def _check_jwt_secret() -> None:
    settings = get_settings()
    if settings.jwt_secret in _INSECURE_SECRETS:
        logger.warning(
            "JWT secret 使用了不安全的默认值，请在 .env 中设置 AISPIDER_JWT_SECRET"
        )


_check_jwt_secret()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """登录获取 JWT token"""
    conn = get_conn()
    try:
        await ensure_user_schema(conn)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    async with conn.pg.connection() as c:
        row = await (await c.execute(
            """
            SELECT username, password_hash, role, is_active
            FROM spider_users
            WHERE username = %s
            LIMIT 1
            """,
            (req.username,),
        )).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    username, password_hash, role, is_active = row
    if not is_active:
        raise HTTPException(status_code=403, detail="User disabled")
    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    settings = get_settings()
    now = time.time()
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        role=role,
    )
