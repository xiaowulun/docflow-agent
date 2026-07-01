"""
任务 API 路由

提供任务的创建、查询、确认、执行等接口。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.app.services.task_service import get_task_service
from packages.schemas.task import TaskStatus

router = APIRouter()


class CreateTaskRequest(BaseModel):
    file_path: str
    user_input: str


class ConfirmTaskRequest(BaseModel):
    task_id: str
    confirmed: bool
    user_input: str | None = None


@router.post("/")
async def create_task(request: CreateTaskRequest):
    """创建任务，分析文件并生成计划"""
    service = get_task_service()
    return service.create_and_plan(request.file_path, request.user_input)


@router.get("/{task_id}")
async def get_task(task_id: str):
    """查询任务状态"""
    service = get_task_service()
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
        "error": task.error_message,
        "confirmation_request": (
            task.confirmation_request.model_dump()
            if task.confirmation_request
            else None
        ),
    }


@router.post("/{task_id}/confirm")
async def confirm_task(task_id: str, request: ConfirmTaskRequest):
    """确认或拒绝执行计划"""
    service = get_task_service()
    try:
        return service.confirm_and_execute(
            task_id,
            request.confirmed,
            user_input=request.user_input,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{task_id}/audit")
async def get_audit_log(task_id: str):
    """获取任务审计日志"""
    service = get_task_service()
    audit_log = service.get_audit_log(task_id)
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return audit_log.model_dump()
