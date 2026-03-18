"""JWT 认证模块"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import jwt

from src.config import get_settings

security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """验证 JWT token，返回 payload"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(*roles: str) -> Callable:
    """角色依赖：仅允许指定角色访问。"""

    async def _checker(payload: dict = Depends(verify_token)) -> dict:
        if roles and payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return payload

    return _checker
