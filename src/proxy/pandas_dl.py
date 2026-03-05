# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import argparse
import requests
import redis
import time
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)


class PandasProxyPoolProtector(object):
    def __init__(self, order_id, api_secret, redis_url, redis_key, pool_size=150, min_duration=5, dedup=False, interval=60):
        """
        熊猫代理-高效代理-不限套餐（企业版）包年 16999
        :param order_id: 熊猫代理订单ID
        :param redis_url: 代理池redis
        :param redis_key:
        :param pool_size: 代理池大小, default: 150
        :param min_duration: 提取的代理ip，稳定时长最小值（分钟）, default: 5
        :param dedup: 是否过滤今日提取过的代理ip, default: False
        :param interval: 检查调度周期（秒）, default: 60
        """
        self.order_id = order_id
        self.api_secret = api_secret
        self.redis_client = redis.StrictRedis.from_url(redis_url)
        self.redis_key = redis_key
        self.pool_size = pool_size
        self.min_duration = min_duration
        self.dedup = dedup
        self.interval = interval

        self.api_url_fmt = "http://www.xiongmaodaili.com/xiongmao-web/apiPlus/vgb?secret={secret}&orderNo={order_id}&count={batch_num}&isTxt=0&proxyType=1&validTime=1&removal=0&cityIds=&returnAccount=1"
        self.sched = BlockingScheduler()

    def get_proxy_list(self, batch_num):
        """
        api提取代理
        :param batch_num:
        :return: `proxy_list` or `[]`
        """
        api_url = self.api_url_fmt.format(secret=self.api_secret, order_id=self.order_id, batch_num=batch_num)
        response = requests.get(api_url)
        if response.status_code == 200 and response.json().get('msg') == "ok":
            return response.json().get('obj')
        return []

    def batch_add_proxy(self, batch_num):
        """
        添加代理->代理池
        :param batch_num:
        """
        if batch_num > 10:
            batch_num = 10
        x = 0
        for proxy_info in self.get_proxy_list(batch_num):
            port = proxy_info.get('port')
            ip = proxy_info.get('ip')
            validTime = proxy_info.get('validTime')
            proxy = ip + ':' + port
            # 将字符串解析为 datetime 对象
            dt = datetime.strptime(validTime, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone('Asia/Shanghai'))
            # 转换为时间戳（秒级）
            timestamp = int(dt.timestamp()) - 10  #设置有效时间前10秒过期
            x += self.redis_client.zadd(self.redis_key, {proxy: timestamp})
        if x:
            logger.info(f'{x} proxies were added to pool.')
            time.sleep(8)

    def check_pool(self):
        """
        检查代理池，数量不足则添加
        """
        while self.redis_client.zcard(self.redis_key) < self.pool_size:
            self.batch_add_proxy(self.pool_size - self.redis_client.zcard(self.redis_key))
        logger.info(f'There are {self.redis_client.zcard(self.redis_key)} proxies.')


    def clean_expired_proxy(self):
        """
        清理过期代理
        """
        x = self.redis_client.zremrangebyscore(self.redis_key, 0, int(time.time()))
        if x:
            logger.info(f'{x} proxies were cleaned up.')

    def run(self):
        logger.info(f'Start proxy pool protector within {self.interval} seconds interval.')
        self.sched.add_job(self.clean_expired_proxy, 'interval', seconds=self.interval, id='clean_expired_proxy')
        self.sched.add_job(self.check_pool, 'interval', seconds=self.interval, id='check_pool', max_instances=2)
        self.sched.start()


if __name__ == '__main__':
    logger.setLevel('DEBUG')
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(module)s[%(lineno)d] - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    orderid = None  # VGB20250408114044Bc7UZCTz
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--order_id', required=True)
    parser.add_argument('-s', '--secret', required=True)
    parser.add_argument('-r', '--redis_url', default='redis://127.0.0.1:6379')
    parser.add_argument('-k', '--redis_key', default='pandas_proxy')
    parser.add_argument('-p', '--pool_size', type=int, default=150)
    args = parser.parse_args()
    p = PandasProxyPoolProtector(order_id=args.order_id, api_secret=args.secret, redis_url=args.redis_url, redis_key=args.redis_key,
                              pool_size=args.pool_size)
    p.run()
