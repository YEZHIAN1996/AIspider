"""钉钉 Webhook 通知"""

from __future__ import annotations

import logging

import httpx

from src.monitor.notifiers import BaseNotifier

logger = logging.getLogger(__name__)


class DingTalkNotifier(BaseNotifier):
    """钉钉机器人 Webhook 通知"""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(self, message: str) -> None:
        payload = {
            "msgtype": "text",
            "text": {"content": message},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self._url, json=payload)
            resp.raise_for_status()


# Backward compatibility for existing imports.
class DingtalkNotifier(DingTalkNotifier):
    pass
