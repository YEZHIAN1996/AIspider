"""Scrapy Extensions for shared resources"""

from scrapy import signals
from twisted.internet import defer

from src.config import get_settings
from src.infra.connections import ConnectionManager


class SharedConnectionExtension:
    """共享连接管理器扩展，确保进程内单例"""

    def __init__(self):
        settings = get_settings()
        self.conn_manager = ConnectionManager(settings)
        self._started = False

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.engine_stopped, signal=signals.engine_stopped)
        return ext

    @defer.inlineCallbacks
    def spider_opened(self, spider):
        if not self._started:
            try:
                yield defer.ensureDeferred(self.conn_manager.startup())
                self._started = True
                spider.logger.info("SharedConnectionExtension: 连接已初始化")
            except Exception:
                spider.logger.exception("SharedConnectionExtension: 连接初始化失败")
                raise

    @defer.inlineCallbacks
    def spider_closed(self, spider, reason):
        # 保持连接打开，供同进程其他 spider 使用
        pass

    @defer.inlineCallbacks
    def engine_stopped(self):
        """引擎停止时清理所有连接"""
        if self._started:
            try:
                yield defer.ensureDeferred(self.conn_manager.shutdown())
                self._started = False
            except Exception:
                pass
