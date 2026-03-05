"""东方财富公告爬虫 - 适配 AIspider"""
from src.spider.base_spider import BaseSpider
from urllib.parse import urlencode
import json


class EastmoneyNoticeSpider(BaseSpider):
    """东方财富股票公告爬虫"""

    name = "eastmoney_notice"
    allowed_domains = ["eastmoney.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "DOWNLOAD_DELAY": 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stock_list = [
            ["600362", "江西铜业", "叶志安"],
            ["601212", "白银有色", "叶志安"],
            ["601127", "赛力斯", "叶志安"],
            ["601899", "紫金矿业", "叶志安"],
            ["600862", "中航高科", "叶志安"],
            ["002460", "赣锋锂业", "会游泳的鱼"],
            ["002151", "北斗星通", "会游泳的鱼"],
            ["600111", "北方稀土", "会游泳的鱼"],
            ["601020", "华钰矿业", "会游泳的鱼"],
            ["603993", "洛阳钼业", "会游泳的鱼"],
        ]

    def start_requests(self):
        """生成初始请求"""
        base_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://data.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        for stock_code, stock_name, user in self.stock_list:
            params = {
                "cb": "jQuery112307770725239396385_1767012132142",
                "sr": "-1",
                "page_size": "50",
                "page_index": "1",
                "ann_type": "A",
                "client_source": "web",
                "stock_list": stock_code,
                "f_node": "0",
                "s_node": "0"
            }

            url = f"{base_url}?{urlencode(params)}"
            yield self.make_request(
                url,
                callback=self.parse,
                headers=headers,
                meta={
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "user": user
                }
            )

    def parse(self, response):
        """解析公告列表"""
        try:
            data = response.text.replace("jQuery112307770725239396385_1767012132142", "")
            json_data = json.loads(data[1:-1])
            items = json_data.get("data", {}).get("list", [])

            for item in items:
                yield {
                    "stock_code": response.meta['stock_code'],
                    "stock_name": response.meta['stock_name'],
                    "user": response.meta['user'],
                    "art_code": item.get("art_code"),
                    "notice_date": item.get("notice_date"),
                    "title": item.get("title"),
                    "detail_url": f"https://data.eastmoney.com/notices/detail/{response.meta['stock_code']}/{item.get('art_code')}.html",
                    "_trace_id": response.meta.get("trace_id"),
                }
                self.stats["items"] += 1

        except Exception as e:
            self.log(f"解析失败: {e}", level="ERROR", url=response.url)
            self.stats["errors"] += 1
