"""任务管理路由

接入 scheduler 模块，提供任务 CRUD、启停控制。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.auth import require_roles
from src.api.deps import get_task_service
from src.scheduler.tasks import TaskValidationError

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    spider_name: str
    schedule_type: str = "cron"
    schedule_expr: str = ""
    spider_args: list[str] = []


class UpdateTaskRequest(BaseModel):
    schedule_type: str | None = None
    schedule_expr: str | None = None
    enabled: bool | None = None
    spider_args: list[str] | None = None


@router.get("/")
async def list_tasks(user: dict = Depends(require_roles("admin", "operator"))):
    """获取任务列表"""
    task_service = get_task_service()
    tasks = await task_service.list_tasks()
    runtime = await task_service.get_runtime_status()
    # 补充进程运行状态
    proc_status = {
        p["spider_name"]: p["status"]
        for p in runtime.get("processes", [])
    }
    result = []
    for t in tasks:
        d = {
            "task_id": t.task_id,
            "spider_name": t.spider_name,
            "schedule_type": t.schedule_type,
            "schedule_expr": t.schedule_expr,
            "enabled": t.enabled,
            "spider_args": t.spider_args,
            "created_at": t.created_at,
            "last_run": t.last_run,
            "status": proc_status.get(t.spider_name, t.status),
        }
        result.append(d)
    return {"tasks": result, "total": len(result)}


@router.post("/")
async def create_task(
    req: CreateTaskRequest,
    user: dict = Depends(require_roles("admin")),
):
    """创建调度任务"""
    task_service = get_task_service()
    try:
        task = await task_service.create_task(
            spider_name=req.spider_name,
            schedule_type=req.schedule_type,
            schedule_expr=req.schedule_expr,
            spider_args=req.spider_args,
        )
    except TaskValidationError as e:
        raise HTTPException(400, str(e))
    return {"msg": "created", "task_id": task.task_id}


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    req: UpdateTaskRequest,
    user: dict = Depends(require_roles("admin")),
):
    """更新任务配置"""
    task_service = get_task_service()
    try:
        task = await task_service.update_task(
            task_id=task_id,
            schedule_type=req.schedule_type,
            schedule_expr=req.schedule_expr,
            enabled=req.enabled,
            spider_args=req.spider_args,
        )
    except TaskValidationError as e:
        raise HTTPException(400, str(e))
    if not task:
        raise HTTPException(404, "Task not found")
    return {"msg": "updated"}


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """手动启动任务（异步投递给 scheduler）"""
    task_service = get_task_service()
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    command_id = await task_service.request_start(task_id)
    return {
        "msg": "start_requested",
        "task_id": task_id,
        "command_id": command_id,
    }


@router.post("/{task_id}/stop")
async def stop_task(
    task_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """停止任务关联的运行中进程（异步投递给 scheduler）"""
    task_service = get_task_service()
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    command_id = await task_service.request_stop(task_id)
    return {
        "msg": "stop_requested",
        "task_id": task_id,
        "command_id": command_id,
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """删除任务"""
    task_service = get_task_service()
    deleted = await task_service.delete_task(task_id)
    if not deleted:
        raise HTTPException(404, "Task not found")
    return {"msg": "deleted"}


@router.get("/commands/{command_id}")
async def get_command_status(
    command_id: str,
    user: dict = Depends(require_roles("admin", "operator")),
):
    """查询命令执行状态（queued/running/success/fail）。"""
    task_service = get_task_service()
    return await task_service.get_command_status(command_id)
