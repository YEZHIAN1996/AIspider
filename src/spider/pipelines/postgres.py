"""PostgreSQL 写入 Pipeline

将校验通过的 item 通过 WriteBuffer 批量写入 PostgreSQL，
校验失败的 item 写入隔离表。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PostgresWriterPipeline:
    """Scrapy Pipeline: 批量写入 PostgreSQL

    使用 WriteBuffer 缓冲数据，达到阈值或超时后批量刷写。
    """

    def open_spider(self, spider):
        self._pg_writer = None
        self._quarantine = None
        self._buffer = None
        self._table = getattr(spider, "result_table", "spider_results")
        self._columns = getattr(spider, "result_columns", [])
        self._warned_not_ready = False
        self._warned_no_columns = False

    async def process_item(self, item, spider):
        data = dict(item)

        # 延迟初始化
        if self._pg_writer is None:
            conn = getattr(spider, "_conn_manager", None)
            if conn and conn.is_started and self._columns:
                from src.writer.pg_writer import PgWriter
                from src.writer.buffer import WriteBuffer
                from src.writer.dead_letter import DeadLetterQueue
                from src.quality.quarantine import QuarantineStore

                self._pg_writer = PgWriter(
                    conn.pg, self._table, self._columns,
                )
                dlq = DeadLetterQueue(conn.redis, target="postgres")
                self._buffer = WriteBuffer(
                    name=f"pg:{self._table}",
                    flush_callback=self._pg_writer.write_batch,
                    max_size=200,
                    flush_interval=3.0,
                    dead_letter_callback=dlq.push_batch,
                )
                self._quarantine = QuarantineStore(conn.pg)
            elif not self._columns and not self._warned_no_columns:
                logger.error(
                    "PG Pipeline 未配置 result_columns，已跳过写入: spider=%s",
                    spider.name,
                )
                self._warned_no_columns = True
            elif (not conn or not conn.is_started) and not self._warned_not_ready:
                logger.error(
                    "PG Pipeline 连接未就绪，暂不可写入: spider=%s",
                    spider.name,
                )
                self._warned_not_ready = True

        # 校验失败 → 隔离表
        errors = data.pop("_quality_errors", None)
        action = data.pop("_quality_action", None)
        if errors and action == "quarantine" and self._quarantine:
            await self._quarantine.store(
                spider_name=spider.name,
                item=data,
                errors=errors,
                trace_id=data.get("_trace_id"),
            )
            return item

        # 通过缓冲区批量写入
        if self._buffer:
            accepted = await self._buffer.add(data)
            if not accepted:
                logger.warning(
                    "PG 写入缓冲区背压，item 被拒绝: spider=%s",
                    spider.name,
                )
        elif not self._warned_not_ready and self._columns:
            logger.error("PG Pipeline 未初始化成功，item 未写入: spider=%s", spider.name)
            self._warned_not_ready = True

        return item

    async def close_spider(self, spider):
        """Spider 关闭时刷写剩余缓冲数据"""
        if self._buffer:
            await self._buffer.flush()
