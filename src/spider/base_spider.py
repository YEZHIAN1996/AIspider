"""BaseSpider 基类

所有业务爬虫的基类，基于 scrapy-redis 的 RedisSpider，
提供 spider_id 生成、trace_id 注入、结构化日志、统一错误处理。
自动初始化 ConnectionManager 供 Pipeline 使用。
"""

from __future__ import annotations

import uuid

import scrapy
from loguru import logger
from scrapy import signals
from scrapy_redis.spiders import RedisSpider
from twisted.internet import defer

from src.config import get_settings
from src.infra.connections import ConnectionManager


class BaseSpider(RedisSpider):
    """所有业务爬虫的基类"""

    custom_settings: dict = {}

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """从 crawler 创建 spider，并绑定生命周期信号。"""
        spider_id = kwargs.get("spider_id") or crawler.settings.get("SPIDER_ID")
        if spider_id:
            kwargs["spider_id"] = spider_id

        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spider_id = kwargs.get(
            "spider_id", f"{self.name}_{uuid.uuid4().hex[:8]}"
        )
        self.stats = {"items": 0, "errors": 0, "requests": 0}
        self._logger = logger.bind(
            spider_id=self.spider_id,
            spider_name=self.name,
        )
        settings = get_settings()
        settings.validate_runtime_safety(service=f"spider-worker:{self.name}")
        # 连接管理器，供 Pipeline 通过 spider._conn_manager 访问
        self._conn_manager = ConnectionManager(settings)
        self._conn_started = False

    @defer.inlineCallbacks
    def spider_opened(self):
        """Spider 打开时初始化连接"""
        if not self._conn_started:
            yield defer.ensureDeferred(self._conn_manager.startup())
            self._conn_started = True
            self.log("ConnectionManager 已初始化")

    @defer.inlineCallbacks
    def spider_closed(self, reason):
        """Spider 关闭时清理连接"""
        if self._conn_started:
            yield defer.ensureDeferred(self._conn_manager.shutdown())
            self._conn_started = False
            self.log(f"ConnectionManager 已关闭, reason={reason}")

    def log(self, message: str, level: str = "INFO", **extra):
        """结构化日志，自动携带 spider 上下文"""
        self._logger.bind(**extra).log(level, message)

    def make_request(self, url, callback, **kwargs):
        """统一构造 Request，自动注入 trace_id"""
        trace_id = uuid.uuid4().hex
        meta = kwargs.pop("meta", {})
        meta["trace_id"] = trace_id
        meta["spider_id"] = self.spider_id
        self.stats["requests"] += 1
        return scrapy.Request(
            url, callback=callback, meta=meta,
            errback=self.handle_error, **kwargs,
        )

    def handle_error(self, failure):
        """统一错误处理"""
        self.stats["errors"] += 1
        self.log(
            f"Request failed: {failure.value}",
            level="ERROR",
            url=failure.request.url,
            trace_id=failure.request.meta.get("trace_id"),
        )
