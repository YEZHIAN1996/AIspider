"""Kafka 实时流 Pipeline

将数据发送到 Kafka topic，
发送失败时写入 Redis 死信队列。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class KafkaStreamPipeline:
    """Scrapy Pipeline: 发送数据到 Kafka 实时流

    发送失败时写入 Redis 死信队列，后台任务定时重放。
    """

    def open_spider(self, spider):
        self._kafka_writer = None
        self._dlq = None
        self._warned_not_ready = False

    async def process_item(self, item, spider):
        data = dict(item)

        # 跳过已隔离的数据
        if data.get("_quality_action") == "quarantine":
            return item

        # 延迟初始化
        if self._kafka_writer is None:
            conn = getattr(spider, "_conn_manager", None)
            if conn and conn.is_started:
                from src.writer.kafka_writer import KafkaWriter
                from src.writer.dead_letter import DeadLetterQueue
                self._kafka_writer = KafkaWriter(conn.kafka)
                self._dlq = DeadLetterQueue(conn.redis)
            elif not self._warned_not_ready:
                logger.error(
                    "Kafka Pipeline 连接未就绪，暂不可写入: spider=%s",
                    spider.name,
                )
                self._warned_not_ready = True

        if self._kafka_writer is None:
            if not self._warned_not_ready:
                logger.error("Kafka Pipeline 未初始化成功，item 未写入: spider=%s", spider.name)
                self._warned_not_ready = True
            return item

        try:
            await self._kafka_writer.send(
                data, key=spider.name,
            )
        except Exception as e:
            logger.warning(
                "Kafka 发送失败，写入死信队列: %s", e,
            )
            if self._dlq:
                try:
                    await self._dlq.push(data, error=str(e))
                except Exception as dlq_err:
                    logger.error(
                        "死信队列写入也失败，数据可能丢失: "
                        "kafka_err=%s, dlq_err=%s, trace_id=%s",
                        e, dlq_err,
                        data.get("_trace_id", "unknown"),
                    )

        return item
