"""通知渠道基类与公共接口"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(self, message: str) -> None:
        """发送通知消息"""
        ...
