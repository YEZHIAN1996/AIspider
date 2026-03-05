"""飞书 Webhook 通知"""

from __future__ import annotations

import logging

import httpx

from src.monitor.notifiers import BaseNotifier

logger = logging.getLogger(__name__)


class FeishuNotifier(BaseNotifier):
    """飞书机器人 Webhook 通知"""

    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(self, message: str) -> None:
        payload = {
            "msg_type": "text",
            "content": {"text": message},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self._url, json=payload)
            resp.raise_for_status()
