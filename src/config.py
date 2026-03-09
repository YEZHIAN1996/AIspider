"""AIspider 统一配置管理

使用 pydantic-settings 从环境变量 / .env 文件加载配置，
所有配置项以 AISPIDER_ 为前缀。
"""

from functools import lru_cache
import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
_INSECURE_MINIO_ACCESS_KEYS = {"minioadmin", ""}
_INSECURE_MINIO_SECRET_KEYS = {"minioadmin", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AISPIDER_",
        case_sensitive=False,
    )

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- PostgreSQL ----
    pg_dsn: str = "postgresql://aispider:aispider@localhost:5432/aispider"
    pg_pool_min: int = Field(default=5, ge=1, le=50)
    pg_pool_max: int = Field(default=20, ge=5, le=200)

    # ---- Kafka ----
    kafka_brokers: str = "localhost:9092"

    # ---- MinIO ----
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_default_bucket: str = "spider-media"

    # ---- JWT ----
    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=1440, ge=5, le=43200)
    auth_bcrypt_rounds: int = Field(default=12, ge=4, le=31)
    bootstrap_admin_username: Optional[str] = None
    bootstrap_admin_password: Optional[str] = None

    # ---- 日志 ----
    log_dir: str = "/var/log/aispider"
    log_level: str = "INFO"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"

    # ---- 调度器 ----
    scheduler_max_workers: int = Field(default=10, ge=1, le=100)
    scheduler_command_status_ttl_seconds: int = Field(default=86400, ge=60, le=604800)
    scheduler_command_dedupe_ttl_seconds: int = Field(default=86400, ge=60, le=604800)

    # ---- 连接管理 ----
    connection_kafka_retry_max: int = Field(default=10, ge=1, le=30)
    connection_kafka_retry_delay_base: int = Field(default=3, ge=1, le=10)
    connection_health_check_interval: int = Field(default=30, ge=5, le=300)

    # ---- 写入缓冲 ----
    buffer_backpressure_multiplier: int = Field(default=2, ge=2, le=10)
    buffer_max_retries: int = Field(default=3, ge=1, le=10)

    # ---- 监控 ----
    watchdog_read_chunk_size: int = Field(default=4096, ge=1024, le=65536)
    watchdog_poll_interval: float = Field(default=10.0, ge=1.0, le=300.0)

    # ---- 代理池 ----
    pandas_proxy_order_id: str = ""
    pandas_proxy_secret: str = ""
    pandas_proxy_redis_key: str = "pandas_proxy"
    pandas_proxy_pool_size: int = 150

    # ---- 告警通知 ----
    wechat_webhook_key: str = ""
    dingtalk_webhook_url: str = ""
    feishu_webhook_url: str = ""

    # ---- 运行环境 ----
    env: str = "dev"
    cors_origins: str = "http://localhost:3001"

    @property
    def is_production(self) -> bool:
        return self.env.strip().lower() in {"prod", "production"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_runtime_safety(self, service: str = "app") -> None:
        """对生产环境执行敏感配置强校验。"""
        errors: list[str] = []

        if self.is_production:
            if self.minio_access_key in _INSECURE_MINIO_ACCESS_KEYS:
                errors.append("AISPIDER_MINIO_ACCESS_KEY uses insecure default in production")
            if self.minio_secret_key in _INSECURE_MINIO_SECRET_KEYS:
                errors.append("AISPIDER_MINIO_SECRET_KEY uses insecure default in production")
            if not self.cors_origins_list:
                errors.append("AISPIDER_CORS_ORIGINS must not be empty in production")
            if "*" in self.cors_origins_list:
                errors.append("AISPIDER_CORS_ORIGINS must not contain '*' in production")

            if errors:
                joined = "; ".join(errors)
                raise ValueError(f"[{service}] unsafe production configuration: {joined}")


@lru_cache
def get_settings() -> Settings:
    """单例获取配置，进程生命周期内只加载一次"""
    return Settings()
