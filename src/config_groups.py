"""配置分组模块

将配置按功能模块分组，提高可维护性。
"""

from pydantic import BaseModel


class RedisConfig(BaseModel):
    """Redis 配置"""
    url: str = "redis://localhost:6379/0"


class PostgresConfig(BaseModel):
    """PostgreSQL 配置"""
    dsn: str = "postgresql://aispider:aispider@localhost:5432/aispider"
    pool_min: int = 5
    pool_max: int = 20


class KafkaConfig(BaseModel):
    """Kafka 配置"""
    brokers: str = "localhost:9092"


class MinIOConfig(BaseModel):
    """MinIO 配置"""
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    default_bucket: str = "spider-media"


class JWTConfig(BaseModel):
    """JWT 认证配置"""
    secret: str
    algorithm: str = "HS256"
    expire_minutes: int = 1440


class LogConfig(BaseModel):
    """日志配置"""
    dir: str = "/var/log/aispider"
    level: str = "INFO"
    rotation: str = "100 MB"
    retention: str = "30 days"


class SchedulerConfig(BaseModel):
    """调度器配置"""
    max_workers: int = 10
    command_status_ttl_seconds: int = 86400
    command_dedupe_ttl_seconds: int = 86400


class ConnectionConfig(BaseModel):
    """连接管理配置"""
    kafka_retry_max: int = 10
    kafka_retry_delay_base: int = 3
    health_check_interval: int = 30


class BufferConfig(BaseModel):
    """写入缓冲配置"""
    backpressure_multiplier: int = 2
    max_retries: int = 3


class MonitorConfig(BaseModel):
    """监控配置"""
    watchdog_read_chunk_size: int = 4096
    watchdog_poll_interval: float = 10.0


class ProxyConfig(BaseModel):
    """代理池配置"""
    pandas_order_id: str = ""
    pandas_secret: str = ""
    pandas_redis_key: str = "pandas_proxy"
    pandas_pool_size: int = 150


class AlertConfig(BaseModel):
    """告警通知配置"""
    wechat_webhook_key: str = ""
    dingtalk_webhook_url: str = ""
    feishu_webhook_url: str = ""
