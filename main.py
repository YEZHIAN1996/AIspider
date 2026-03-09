#!/usr/bin/env python3
"""AIspider 统一启动入口

Usage:
    python main.py all          # 启动所有服务
    python main.py api          # 仅启动 API 网关
    python main.py scheduler    # 仅启动调度器
    python main.py worker       # 仅启动 Worker
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))


def start_api():
    """启动 API 网关"""
    import uvicorn
    from src.api.main import create_app

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


def start_scheduler():
    """启动调度器"""
    import asyncio
    from src.scheduler.main import main as scheduler_main

    asyncio.run(scheduler_main())


def start_worker():
    """启动 Scrapy 分布式 Worker"""
    import subprocess
    # 启动 scrapy-redis 分布式 worker，从 Redis 队列获取任务
    subprocess.run(["scrapy", "runspider", "src/spider/spiders/example_spider.py"], check=False)


async def start_all():
    """启动所有服务（开发模式）"""
    import multiprocessing

    processes = []

    # 启动 API
    p_api = multiprocessing.Process(target=start_api, name="api")
    p_api.start()
    processes.append(p_api)

    # 启动调度器
    p_scheduler = multiprocessing.Process(target=start_scheduler, name="scheduler")
    p_scheduler.start()
    processes.append(p_scheduler)

    print("✅ 所有服务已启动")
    print("  - API: http://localhost:8000")
    print("  - Scheduler: 运行中")
    print("\n按 Ctrl+C 停止所有服务")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        for p in processes:
            p.terminate()
            p.join()
        print("✅ 所有服务已停止")


def main():
    parser = argparse.ArgumentParser(description="AIspider 统一启动入口")
    parser.add_argument(
        "mode",
        choices=["all", "api", "scheduler", "worker"],
        help="启动模式",
    )
    args = parser.parse_args()

    if args.mode == "all":
        asyncio.run(start_all())
    elif args.mode == "api":
        start_api()
    elif args.mode == "scheduler":
        start_scheduler()
    elif args.mode == "worker":
        start_worker()


if __name__ == "__main__":
    main()
