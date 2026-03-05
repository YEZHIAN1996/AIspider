"""监控告警测试"""
import pytest
from src.monitor.alert_consumer import AlertConsumer


def test_alert_keyword_matching():
    """测试告警关键词匹配"""
    consumer = AlertConsumer("localhost:9092", [])

    log_entry = {
        "message": "Database connection ERROR",
        "level": "ERROR",
        "module": "spider"
    }

    # 验证关键词匹配逻辑
    assert any(kw in log_entry["message"] for kw in consumer.ALERT_KEYWORDS)


def test_aggregate_window():
    """测试告警聚合窗口"""
    consumer = AlertConsumer("localhost:9092", [])

    key = "ERROR:spider"
    assert consumer._check_aggregate(key) is True
    assert consumer._check_aggregate(key) is True
    assert consumer._check_aggregate(key) is True
    # 第4次应该被限制
    assert consumer._check_aggregate(key) is False
