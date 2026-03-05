"""爬虫调度模块公共接口"""

from src.scheduler.lock import acquire_scheduler_lock
from src.scheduler.main import SpiderScheduler
from src.scheduler.service import TaskService
from src.scheduler.tasks import SpiderTask, TaskStore

__all__ = [
    "SpiderScheduler",
    "TaskService",
    "SpiderTask",
    "TaskStore",
    "acquire_scheduler_lock",
]
