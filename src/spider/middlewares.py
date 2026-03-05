"""Scrapy 下载中间件

包含代理注入、重试策略、UA 轮换。
"""

from __future__ import annotations

import random
import logging

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware as _BaseRetry

logger = logging.getLogger(__name__)

# 常用 User-Agent 池
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class ProxyMiddleware:
    """代理注入中间件

    从 Redis 代理池获取代理 IP 注入到请求中。
    当前为预留实现，后续对接 proxy 模块。
    """

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(
            middleware.spider_opened, signal=signals.spider_opened,
        )
        return middleware

    def spider_opened(self, spider):
        logger.info("ProxyMiddleware 已启用: %s", spider.name)

    def process_request(self, request, spider):
        # 预留：后续从 proxy 模块获取代理
        # proxy = await proxy_pool.get_proxy()
        # request.meta["proxy"] = proxy.url
        pass


class UserAgentMiddleware:
    """UA 轮换中间件，每次请求随机选择 User-Agent"""

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(_USER_AGENTS)


class RetryMiddleware(_BaseRetry):
    """增强重试中间件

    在 Scrapy 默认重试基础上增加日志记录。
    """

    def _retry(self, request, reason, spider):
        logger.warning(
            "重试请求: url=%s, reason=%s, retries=%d",
            request.url, reason,
            request.meta.get("retry_times", 0),
        )
        return super()._retry(request, reason, spider)
