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

    @property
    def _conn_manager(self):
        """从 extension 获取共享连接管理器"""
        ext = self.crawler.extensions.get("SharedConnectionExtension")
        if ext is None:
            raise RuntimeError("SharedConnectionExtension 未启用")
        return ext.conn_manager

    def spider_opened(self):
        """Spider 打开时的钩子"""
        self.log("Spider 已启动")

    def spider_closed(self, reason):
        """Spider 关闭时的钩子"""
        self.log(f"Spider 已关闭, reason={reason}")

    def log(self, message: str, level: str = "INFO", **extra):
        """结构化日志，自动携带 spider 上下文"""
        from src.logger.filters import filter_sensitive_data
        filtered_extra = filter_sensitive_data(extra)
        self._logger.bind(**filtered_extra).log(level, message)

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
