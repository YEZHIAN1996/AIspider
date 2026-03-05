"""Kafka 数据发送模块

将清洗后的数据发送到 Kafka topic，
按 spider_name 分区保证同一爬虫数据有序。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

from src.infra.metrics import (
    WRITE_FAIL_TOTAL,
    WRITE_LATENCY,
    WRITE_SUCCESS_TOTAL,
)

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaWriter:
    """Kafka 数据写入器

    Args:
        producer: aiokafka AIOKafkaProducer 实例
        topic: 目标 Kafka topic
    """

    def __init__(
        self,
        producer: AIOKafkaProducer,
        topic: str = "spider_data",
    ) -> None:
        self._producer = producer
        self._topic = topic

    async def send(self, item: dict, key: str | None = None) -> None:
        """发送单条数据到 Kafka

        Args:
            item: 数据字典
            key: 分区键（通常为 spider_name）
        """
        payload = json.dumps(item, ensure_ascii=False).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None
        start = time.monotonic()

        try:
            await self._producer.send_and_wait(
                self._topic, payload, key=key_bytes,
            )
            elapsed = time.monotonic() - start
            WRITE_SUCCESS_TOTAL.labels(target="kafka").inc()
            WRITE_LATENCY.labels(target="kafka").observe(elapsed)
        except Exception:
            WRITE_FAIL_TOTAL.labels(target="kafka").inc()
            logger.exception("Kafka 发送失败: topic=%s", self._topic)
            raise

    async def send_batch(
        self, items: list[dict], key: str | None = None,
    ) -> int:
        """批量发送数据到 Kafka

        Returns:
            成功发送的条数
        """
        sent = 0
        for item in items:
            try:
                await self.send(item, key=key)
                sent += 1
            except Exception:
                # 单条失败不中断整批，由调用方决定重试策略
                pass
        return sent
