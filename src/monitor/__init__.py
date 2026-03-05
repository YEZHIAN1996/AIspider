"""监控告警模块公共接口

通知器按需导入，避免顶层依赖 httpx 等可选包。
"""

from src.monitor.alert_consumer import AlertConsumer
from src.monitor.notifiers import BaseNotifier

__all__ = [
    "AlertConsumer",
    "BaseNotifier",
]
