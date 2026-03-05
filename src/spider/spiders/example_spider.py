"""示例爬虫

演示如何基于 BaseSpider 编写业务爬虫。
"""

from src.spider.base_spider import BaseSpider


class ExampleSpider(BaseSpider):
    """示例爬虫，演示 BaseSpider 用法"""

    name = "example_spider"
    redis_key = "queue:example_spider"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 1.0,
    }
    result_table = "spider_results"
    result_columns = [
        "spider_name",
        "spider_id",
        "trace_id",
        "url",
        "data",
    ]

    def parse(self, response):
        self.stats["items"] += 1
        trace_id = response.meta.get("trace_id", "")

        yield {
            "spider_name": self.name,
            "spider_id": self.spider_id,
            "trace_id": trace_id,
            "url": response.url,
            "data": {
                "title": response.css("title::text").get(""),
                "status": response.status,
            },
            "_trace_id": trace_id,
            "_spider_id": self.spider_id,
        }
