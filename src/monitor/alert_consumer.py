"""Kafka 日志消费 + 告警

从 Kafka 消费日志，匹配告警规则，
通过滑动窗口聚合防止告警风暴。
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from src.monitor.rule_engine import AlertRuleEngine

if TYPE_CHECKING:
    from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class AlertConsumer:
    """从 Kafka 消费日志，匹配告警规则

    滑动窗口聚合：同一规则在窗口内最多触发 N 次通知。
    """

    ALERT_KEYWORDS = [
        "ERROR", "CRITICAL", "Exception",
        "Traceback", "OOM",
    ]
    AGGREGATE_WINDOW = 300  # 5 分钟窗口
    AGGREGATE_MAX = 3       # 窗口内最多告警 3 次
    _CLEANUP_INTERVAL = 100  # 每处理 100 条消息清理一次过期 key

    def __init__(
        self,
        kafka_brokers: str,
        notifiers: list,
        rule_engine: AlertRuleEngine | None = None,
    ) -> None:
        self._kafka_brokers = kafka_brokers
        self._notifiers = notifiers
        self._rule_engine = rule_engine
        self._consumer: AIOKafkaConsumer | None = None
        self._alert_counts: dict[str, list[float]] = defaultdict(list)
        self._msg_counter: int = 0

    async def start(self) -> None:
        """启动 Kafka 消费者"""
        from aiokafka import AIOKafkaConsumer

        self._consumer = AIOKafkaConsumer(
            "spider_logs",
            bootstrap_servers=self._kafka_brokers,
            group_id="alert_consumer",
            value_deserializer=lambda m: json.loads(m),
        )
        await self._consumer.start()
        logger.info("告警消费者已启动")

    async def stop(self) -> None:
        """停止消费者"""
        if self._consumer:
            await self._consumer.stop()

    async def consume_loop(self) -> None:
        """主消费循环"""
        if not self._consumer:
            return
        async for msg in self._consumer:
            await self._process_message(msg.value)

    async def _process_message(self, log_entry: dict) -> None:
        """处理单条日志，匹配告警规则"""
        self._msg_counter += 1
        if self._msg_counter % self._CLEANUP_INTERVAL == 0:
            self._cleanup_stale_keys()

        if self._rule_engine:
            matched_rules = self._rule_engine.match_rules(log_entry)
            for rule in matched_rules:
                key = f"{rule.name}:{log_entry.get('module', '')}"
                if self._check_aggregate(key):
                    await self._send_alert(log_entry, rule.name, rule.level.value)
        else:
            message = log_entry.get("message", "")
            for keyword in self.ALERT_KEYWORDS:
                if keyword in message:
                    key = f"{keyword}:{log_entry.get('module', '')}"
                    if self._check_aggregate(key):
                        await self._send_alert(log_entry, keyword, "critical")
                    break

    def _cleanup_stale_keys(self) -> None:
        """清理窗口期外的空 key，防止字典无限增长"""
        now = time.time()
        stale = [
            k for k, v in self._alert_counts.items()
            if not v or (now - max(v)) > self.AGGREGATE_WINDOW
        ]
        for k in stale:
            del self._alert_counts[k]

    def _check_aggregate(self, key: str) -> bool:
        """滑动窗口聚合，防止告警风暴"""
        now = time.time()
        self._alert_counts[key] = [
            t for t in self._alert_counts[key]
            if now - t < self.AGGREGATE_WINDOW
        ]
        if len(self._alert_counts[key]) >= self.AGGREGATE_MAX:
            return False
        self._alert_counts[key].append(now)
        return True

    async def _send_alert(self, log_entry: dict, rule_name: str, level: str) -> None:
        """通过所有通知渠道发送告警"""
        alert_msg = (
            f"[AIspider 告警] {rule_name} [{level.upper()}]\n"
            f"模块: {log_entry.get('module', 'unknown')}\n"
            f"Spider: {log_entry.get('spider_id', '')}\n"
            f"消息: {log_entry.get('message', '')}\n"
            f"时间: {log_entry.get('timestamp', '')}"
        )
        for notifier in self._notifiers:
            try:
                await notifier.send(alert_msg)
            except Exception:
                logger.exception("告警发送失败: %s", type(notifier).__name__)


async def _run_standalone() -> None:
    """独立进程运行告警消费者"""
    import asyncio
    import signal
    import os

    from src.config import get_settings
    from src.logger.intercept import intercept_stdlib_logging
    from src.monitor.notifiers.wechat import WechatNotifier
    from src.monitor.notifiers.dingtalk import DingTalkNotifier
    from src.monitor.notifiers.feishu import FeishuNotifier

    intercept_stdlib_logging()
    settings = get_settings()
    settings.validate_runtime_safety(service="monitor")

    notifiers = []
    if settings.wechat_webhook_key:
        notifiers.append(WechatNotifier(settings.wechat_webhook_key))
    if settings.dingtalk_webhook_url:
        notifiers.append(DingTalkNotifier(settings.dingtalk_webhook_url))
    if settings.feishu_webhook_url:
        notifiers.append(FeishuNotifier(settings.feishu_webhook_url))

    rule_engine = None
    rule_file = os.getenv("ALERT_RULES_FILE", "alert_rules.yaml")
    if os.path.exists(rule_file):
        try:
            rule_engine = AlertRuleEngine.from_yaml(rule_file)
            logger.info(f"已加载 {len(rule_engine.rules)} 条告警规则")
        except Exception as e:
            logger.warning(f"加载告警规则失败，使用默认规则: {e}")

    consumer = AlertConsumer(
        kafka_brokers=settings.kafka_brokers,
        notifiers=notifiers,
        rule_engine=rule_engine,
    )

    # Kafka 可能还没就绪，重试连接
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            await consumer.start()
            break
        except Exception as e:
            if attempt == max_retries:
                logger.error("Kafka 连接失败，已达最大重试次数: %s", e)
                return
            logger.warning(
                "Kafka 连接失败，%d秒后重试 (%d/%d): %s",
                attempt * 3, attempt, max_retries, e,
            )
            await asyncio.sleep(attempt * 3)

    stop_event = asyncio.Event()

    def _handle_signal():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("告警消费者独立进程已启动")

    consume_task = asyncio.create_task(consumer.consume_loop())
    await stop_event.wait()
    consume_task.cancel()

    await consumer.stop()
    logger.info("告警消费者独立进程已退出")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_run_standalone())
