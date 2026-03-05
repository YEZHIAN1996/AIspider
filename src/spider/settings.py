"""Scrapy 全局设置

scrapy-redis 分布式配置 + Pipeline 执行顺序 + 中间件配置。
"""

import os

# ============================================================
# 基础配置
# ============================================================

BOT_NAME = "aispider"
SPIDER_MODULES = ["src.spider.spiders"]
NEWSPIDER_MODULE = "src.spider.spiders"

ROBOTSTXT_OBEY = False
LOG_ENABLED = False  # 由 Loguru 接管日志

# 使用 asyncio reactor，使 Pipeline 中的 async def process_item 正常工作
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# ============================================================
# scrapy-redis 分布式配置
# ============================================================

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.PriorityQueue"

REDIS_URL = os.getenv("AISPIDER_REDIS_URL", "redis://localhost:6379/0")

# ============================================================
# 并发与限速
# ============================================================

CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3

# ============================================================
# Pipeline 执行顺序
# ============================================================

ITEM_PIPELINES = {
    "src.spider.pipelines.quality.DataQualityPipeline": 100,
    "src.spider.pipelines.media.MinIOMediaPipeline": 200,
    "src.spider.pipelines.postgres.PostgresWriterPipeline": 300,
    "src.spider.pipelines.kafka.KafkaStreamPipeline": 400,
}

# ============================================================
# 下载中间件
# ============================================================

DOWNLOADER_MIDDLEWARES = {
    "src.spider.middlewares.ProxyMiddleware": 100,
    "src.spider.middlewares.RetryMiddleware": 200,
    "src.spider.middlewares.UserAgentMiddleware": 300,
}

# ============================================================
# 请求头
# ============================================================

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
