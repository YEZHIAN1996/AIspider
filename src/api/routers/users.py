"""用户管理路由（admin only）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg import errors as pg_errors

from src.api.auth import require_roles
from src.api.deps import get_conn
from src.api.user_repo import ensure_user_schema, hash_password
from src.config import get_settings

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = "operator"


class UpdatePasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UpdateStatusRequest(BaseModel):
    is_active: bool


@router.get("/")
async def list_users(user: dict = Depends(require_roles("admin"))):
    conn = get_conn()
    try:
        await ensure_user_schema(conn)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    async with conn.pg.connection() as c:
        cur = await c.execute(
            """
            SELECT username, role, is_active, created_at, updated_at
            FROM spider_users
            ORDER BY username ASC
            """
        )
        rows = await cur.fetchall()
    return {
        "users": [
            {
                "username": r[0],
                "role": r[1],
                "is_active": r[2],
                "created_at": r[3],
                "updated_at": r[4],
            }
            for r in rows
        ]
    }


@router.post("/")
async def create_user(
    req: CreateUserRequest,
    user: dict = Depends(require_roles("admin")),
):
    if req.role not in {"admin", "operator"}:
        raise HTTPException(400, "role must be admin or operator")

    conn = get_conn()
    try:
        await ensure_user_schema(conn)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    settings = get_settings()
    pwd_hash = hash_password(req.password, settings.auth_bcrypt_rounds)

    async with conn.pg.connection() as c:
        try:
            await c.execute(
                """
                INSERT INTO spider_users (username, password_hash, role)
                VALUES (%s, %s, %s)
                """,
                (req.username, pwd_hash, req.role),
            )
            await c.commit()
        except pg_errors.UniqueViolation:
            await c.rollback()
            raise HTTPException(409, "username already exists")
        except Exception:
            await c.rollback()
            raise HTTPException(500, "failed to create user")

    return {"msg": "created", "username": req.username, "role": req.role}


@router.put("/{username}/password")
async def update_password(
    username: str,
    req: UpdatePasswordRequest,
    user: dict = Depends(require_roles("admin")),
):
    conn = get_conn()
    try:
        await ensure_user_schema(conn)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    settings = get_settings()
    pwd_hash = hash_password(req.password, settings.auth_bcrypt_rounds)

    async with conn.pg.connection() as c:
        cur = await c.execute(
            """
            UPDATE spider_users
            SET password_hash = %s, updated_at = now()
            WHERE username = %s
            """,
            (pwd_hash, username),
        )
        await c.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "User not found")
    return {"msg": "password_updated", "username": username}


@router.put("/{username}/status")
async def update_status(
    username: str,
    req: UpdateStatusRequest,
    user: dict = Depends(require_roles("admin")),
):
    if username == user.get("sub") and not req.is_active:
        raise HTTPException(400, "cannot disable yourself")

    conn = get_conn()
    try:
        await ensure_user_schema(conn)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    async with conn.pg.connection() as c:
        cur = await c.execute(
            """
            UPDATE spider_users
            SET is_active = %s, updated_at = now()
            WHERE username = %s
            """,
            (req.is_active, username),
        )
        await c.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "User not found")
    return {"msg": "status_updated", "username": username, "is_active": req.is_active}
