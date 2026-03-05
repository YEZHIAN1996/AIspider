"""Prometheus 指标定义

集中定义所有模块的 Prometheus 指标，
各模块通过 import 使用，避免指标重复注册。
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
)

# ============================================================
# 种子模块 (seed)
# ============================================================

SEED_QUEUE_SIZE = Gauge(
    "seed_queue_size",
    "当前种子队列长度",
    ["spider_name"],
)

SEED_ENQUEUED_TOTAL = Counter(
    "seed_enqueued_total",
    "种子入队总数",
    ["spider_name"],
)

SEED_DEQUEUED_TOTAL = Counter(
    "seed_dequeued_total",
    "种子出队总数",
    ["spider_name"],
)

SEED_DUPLICATED_TOTAL = Counter(
    "seed_duplicated_total",
    "去重拦截总数",
    ["spider_name"],
)

# ============================================================
# 代理模块 (proxy)
# ============================================================

PROXY_POOL_SIZE = Gauge(
    "proxy_pool_size",
    "代理池当前可用数量",
)

PROXY_REQUEST_TOTAL = Counter(
    "proxy_request_total",
    "代理请求总数",
    ["protocol", "result"],  # result: success | fail
)

PROXY_LATENCY = Histogram(
    "proxy_latency_seconds",
    "代理请求延迟",
    ["protocol"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ============================================================
# 爬虫模块 (spider)
# ============================================================

SPIDER_ITEMS_TOTAL = Counter(
    "spider_items_total",
    "爬虫抓取 item 总数",
    ["spider_name", "spider_id"],
)

SPIDER_REQUESTS_TOTAL = Counter(
    "spider_requests_total",
    "爬虫发出请求总数",
    ["spider_name", "spider_id"],
)

SPIDER_ERRORS_TOTAL = Counter(
    "spider_errors_total",
    "爬虫错误总数",
    ["spider_name", "spider_id", "error_type"],
)

# ============================================================
# 数据写入模块 (writer)
# ============================================================

WRITE_SUCCESS_TOTAL = Counter(
    "write_success_total",
    "写入成功总数",
    ["target"],  # postgres | kafka | minio
)

WRITE_FAIL_TOTAL = Counter(
    "write_fail_total",
    "写入失败总数",
    ["target"],
)

WRITE_LATENCY = Histogram(
    "write_latency_seconds",
    "写入延迟",
    ["target"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0),
)

WRITE_BUFFER_SIZE = Gauge(
    "write_buffer_size",
    "当前写入缓冲区大小",
    ["target"],
)

DEAD_LETTER_SIZE = Gauge(
    "dead_letter_queue_size",
    "死信队列积压量",
)

# ============================================================
# 数据质量模块 (quality)
# ============================================================

QUALITY_TOTAL = Counter(
    "data_quality_total",
    "校验 item 总数",
    ["spider_name"],
)

QUALITY_PASSED = Counter(
    "data_quality_passed",
    "校验通过总数",
    ["spider_name"],
)

QUALITY_FAILED = Counter(
    "data_quality_failed",
    "校验失败总数",
    ["spider_name", "field", "reason"],
)

# ============================================================
# 调度器模块 (scheduler)
# ============================================================

SCHEDULER_TASKS_RUNNING = Gauge(
    "scheduler_tasks_running",
    "当前运行中的爬虫任务数",
)

SCHEDULER_TASK_EXECUTIONS = Counter(
    "scheduler_task_executions_total",
    "任务执行总次数",
    ["spider_name", "result"],  # result: success | fail | timeout
)

# ============================================================
# 应用信息
# ============================================================

APP_INFO = Info(
    "aispider",
    "AIspider 应用信息",
)
