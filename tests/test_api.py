"""API 路由测试示例"""
import pytest
from httpx import AsyncClient
from src.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """测试登录失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={
            "username": "invalid",
            "password": "wrong"
        })
        assert response.status_code == 401
