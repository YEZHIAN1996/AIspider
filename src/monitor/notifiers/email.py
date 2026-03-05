"""邮件 SMTP 通知"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from src.monitor.notifiers import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """SMTP 邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        recipients: list[str],
    ) -> None:
        self._host = smtp_host
        self._port = smtp_port
        self._username = username
        self._password = password
        self._sender = sender
        self._recipients = recipients

    async def send(self, message: str) -> None:
        def _send_blocking() -> None:
            msg = MIMEText(message, "plain", "utf-8")
            msg["Subject"] = "[AIspider] 告警通知"
            msg["From"] = self._sender
            msg["To"] = ", ".join(self._recipients)

            with smtplib.SMTP_SSL(self._host, self._port) as server:
                server.login(self._username, self._password)
                server.sendmail(
                    self._sender, self._recipients, msg.as_string(),
                )

        await asyncio.to_thread(_send_blocking)
