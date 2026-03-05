"""配置管理测试"""
import pytest
from src.config import Settings


def test_settings_defaults():
    """测试默认配置"""
    settings = Settings()
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.log_level == "INFO"
    assert settings.jwt_algorithm == "HS256"


def test_settings_from_env(monkeypatch):
    """测试从环境变量加载"""
    monkeypatch.setenv("AISPIDER_REDIS_URL", "redis://custom:6379/1")
    monkeypatch.setenv("AISPIDER_LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.redis_url == "redis://custom:6379/1"
    assert settings.log_level == "DEBUG"
