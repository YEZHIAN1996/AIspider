"""Loguru 自定义 sink 和异步分发器。

包含：
- Kafka 远程日志 sink（带队列、重试、丢弃保护）
- Redis PubSub 日志 sink（带队列、重试、丢弃保护）
- 日志采样过滤器
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer
    from loguru import Record

logger = logging.getLogger(__name__)


class SamplingFilter:
    """日志采样过滤器。"""

    def __init__(
        self,
        debug_rate: float = 0.01,
        info_rate: float = 0.1,
    ) -> None:
        self.debug_rate = debug_rate
        self.info_rate = info_rate

    def __call__(self, record: Record) -> bool:
        level = record["level"].name
        if level == "DEBUG":
            return random.random() < self.debug_rate
        if level == "INFO":
            return random.random() < self.info_rate
        return True


@dataclass
class _KafkaEnvelope:
    payload: bytes
    retry: int = 0
    next_retry_at: float = 0.0


@dataclass
class _RedisEnvelope:
    channel: str
    payload: str
    retry: int = 0
    next_retry_at: float = 0.0


class AsyncLogDispatcher:
    """日志异步分发器。

    Sink 回调只负责将消息放入线程安全队列；真正 I/O 由事件循环内 worker 完成。
    """

    def __init__(
        self,
        max_queue_size: int = 20_000,
        max_retries: int = 3,
    ) -> None:
        self._max_retries = max_retries
        self._kafka_queue: queue.Queue[_KafkaEnvelope] = queue.Queue(maxsize=max_queue_size)
        self._redis_queue: queue.Queue[_RedisEnvelope] = queue.Queue(maxsize=max_queue_size)
        self._producer: AIOKafkaProducer | None = None
        self._redis = None
        self._tasks: list[asyncio.Task] = []
        self._running = False

        self._dropped_kafka = 0
        self._dropped_redis = 0

    async def start(self, producer: AIOKafkaProducer, redis) -> None:
        if self._running:
            return
        self._producer = producer
        self._redis = redis
        self._running = True
        self._tasks = [
            asyncio.create_task(self._kafka_loop()),
            asyncio.create_task(self._redis_loop()),
        ]
        logger.info("日志分发器已启动")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info(
            "日志分发器已停止: dropped_kafka=%d dropped_redis=%d",
            self._dropped_kafka, self._dropped_redis,
        )

    def enqueue_kafka(self, payload: bytes) -> None:
        try:
            self._kafka_queue.put_nowait(_KafkaEnvelope(payload=payload))
        except queue.Full:
            self._dropped_kafka += 1
            if self._dropped_kafka % 100 == 1:
                logger.warning("Kafka 日志队列已满，开始丢弃: dropped=%d", self._dropped_kafka)

    def enqueue_redis(self, channel: str, payload: str) -> None:
        try:
            self._redis_queue.put_nowait(
                _RedisEnvelope(channel=channel, payload=payload),
            )
        except queue.Full:
            self._dropped_redis += 1
            if self._dropped_redis % 100 == 1:
                logger.warning("Redis 日志队列已满，开始丢弃: dropped=%d", self._dropped_redis)

    async def _kafka_loop(self) -> None:
        while self._running or not self._kafka_queue.empty():
            env = self._pop_kafka()
            if env is None:
                await asyncio.sleep(0.05)
                continue
            now = time.monotonic()
            if env.next_retry_at > now:
                self._requeue_kafka(env)
                await asyncio.sleep(min(env.next_retry_at - now, 0.2))
                continue
            try:
                if self._producer is None:
                    raise RuntimeError("Kafka producer not initialized")
                await self._producer.send_and_wait("spider_logs", env.payload)
            except Exception as e:
                if env.retry < self._max_retries:
                    env.retry += 1
                    env.next_retry_at = time.monotonic() + min(0.2 * (2 ** env.retry), 5.0)
                    self._requeue_kafka(env)
                else:
                    self._dropped_kafka += 1
                    logger.error("Kafka 日志发送失败并丢弃: %s", e)

    async def _redis_loop(self) -> None:
        while self._running or not self._redis_queue.empty():
            env = self._pop_redis()
            if env is None:
                await asyncio.sleep(0.05)
                continue
            now = time.monotonic()
            if env.next_retry_at > now:
                self._requeue_redis(env)
                await asyncio.sleep(min(env.next_retry_at - now, 0.2))
                continue
            try:
                if self._redis is None:
                    raise RuntimeError("Redis client not initialized")
                await self._redis.publish(env.channel, env.payload)
            except Exception as e:
                if env.retry < self._max_retries:
                    env.retry += 1
                    env.next_retry_at = time.monotonic() + min(0.2 * (2 ** env.retry), 5.0)
                    self._requeue_redis(env)
                else:
                    self._dropped_redis += 1
                    logger.error("Redis 日志发布失败并丢弃: %s", e)

    def _pop_kafka(self) -> _KafkaEnvelope | None:
        try:
            return self._kafka_queue.get_nowait()
        except queue.Empty:
            return None

    def _pop_redis(self) -> _RedisEnvelope | None:
        try:
            return self._redis_queue.get_nowait()
        except queue.Empty:
            return None

    def _requeue_kafka(self, env: _KafkaEnvelope) -> None:
        try:
            self._kafka_queue.put_nowait(env)
        except queue.Full:
            self._dropped_kafka += 1

    def _requeue_redis(self, env: _RedisEnvelope) -> None:
        try:
            self._redis_queue.put_nowait(env)
        except queue.Full:
            self._dropped_redis += 1


class KafkaSink:
    """将日志入队到 Kafka 分发器。"""

    def __init__(self, dispatcher: AsyncLogDispatcher) -> None:
        self._dispatcher = dispatcher

    def __call__(self, message: str) -> None:
        record = message.record
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "module": record["extra"].get("module", "unknown"),
            "spider_id": record["extra"].get("spider_id", ""),
            "trace_id": record["extra"].get("trace_id", ""),
            "message": record["message"],
            "file": f"{record['file'].name}:{record['line']}",
            "function": record["function"],
        }
        if record["exception"] is not None:
            log_entry["exception"] = str(record["exception"])
        payload = json.dumps(log_entry, ensure_ascii=False).encode("utf-8")
        self._dispatcher.enqueue_kafka(payload)


class RedisPubSubSink:
    """将日志入队到 Redis PubSub 分发器。"""

    def __init__(self, dispatcher: AsyncLogDispatcher, channel_prefix: str = "logs") -> None:
        self._dispatcher = dispatcher
        self._channel_prefix = channel_prefix

    def __call__(self, message: str) -> None:
        record = message.record
        spider_id = record["extra"].get("spider_id", "system")
        channel = f"{self._channel_prefix}:{spider_id}"
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "module": record["extra"].get("module", "unknown"),
            "spider_id": spider_id,
            "message": record["message"],
        }
        payload = json.dumps(log_entry, ensure_ascii=False)
        self._dispatcher.enqueue_redis(channel, payload)


_dispatcher = AsyncLogDispatcher()


async def start_log_workers(producer: AIOKafkaProducer, redis) -> None:
    """启动日志分发 worker。"""
    await _dispatcher.start(producer, redis)


async def stop_log_workers() -> None:
    """停止日志分发 worker。"""
    await _dispatcher.stop()


def attach_kafka_sink(_producer=None, _topic: str = "spider_logs") -> int:
    """挂载 Kafka sink，返回 handler id。"""
    from loguru import logger as loguru_logger

    sink = KafkaSink(_dispatcher)
    return loguru_logger.add(
        sink,
        filter=SamplingFilter(),
        level="DEBUG",
        enqueue=True,
    )


def attach_redis_pubsub_sink(_redis=None, channel_prefix: str = "logs") -> int:
    """挂载 Redis PubSub sink，返回 handler id。"""
    from loguru import logger as loguru_logger

    sink = RedisPubSubSink(_dispatcher, channel_prefix)
    return loguru_logger.add(
        sink,
        filter=SamplingFilter(debug_rate=0.0, info_rate=0.5),
        level="INFO",
        enqueue=True,
    )
