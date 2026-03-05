"""企业微信通知器"""

from __future__ import annotations

import logging

import httpx

from src.monitor.notifiers import BaseNotifier

logger = logging.getLogger(__name__)


class WechatNotifier(BaseNotifier):
    """企业微信 Webhook 通知"""

    def __init__(self, webhook_key: str) -> None:
        self._url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        self._key = webhook_key

    async def send(self, message: str) -> None:
        """发送文本消息。"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self._url,
                    params={"key": self._key},
                    json={"msgtype": "text", "text": {"content": message}},
                )
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") != 0:
                raise RuntimeError(f"企业微信发送失败: {result}")
        except Exception as e:
            logger.exception("企业微信发送异常: %s", e)
            raise
