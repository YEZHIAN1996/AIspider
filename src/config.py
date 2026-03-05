"""AIspider 统一配置管理

使用 pydantic-settings 从环境变量 / .env 文件加载配置，
所有配置项以 AISPIDER_ 为前缀。
"""

from functools import lru_cache
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
_INSECURE_SECRETS = {"change-me-in-production", "secret", ""}
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
    pg_pool_min: int = 5
    pg_pool_max: int = 20

    # ---- Kafka ----
    kafka_brokers: str = "localhost:9092"

    # ---- MinIO ----
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_default_bucket: str = "spider-media"

    # ---- JWT ----
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h
    auth_bcrypt_rounds: int = 12
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None

    # ---- 日志 ----
    log_dir: str = "/var/log/aispider"
    log_level: str = "INFO"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"

    # ---- 调度器 ----
    scheduler_max_workers: int = 10
    scheduler_command_status_ttl_seconds: int = 86400
    scheduler_command_dedupe_ttl_seconds: int = 86400

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
        if not self.is_production:
            if self.jwt_secret in _INSECURE_SECRETS:
                logger.warning(
                    "[%s] JWT secret 使用默认/弱值，开发环境可运行，生产环境会拒绝启动",
                    service,
                )
            return

        errors: list[str] = []
        if self.jwt_secret in _INSECURE_SECRETS:
            errors.append("AISPIDER_JWT_SECRET is insecure in production")
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
