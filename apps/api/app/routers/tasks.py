"""
任务 API 路由

提供任务的创建、查询、确认、执行等接口。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 临时使用内存存储，后续换 SQLite
_orchestrators: dict = {}


class CreateTaskRequest(BaseModel):
    file_path: str
    user_input: str


class ConfirmTaskRequest(BaseModel):
    task_id: str
    confirmed: bool


@router.post("/")
async def create_task(request: CreateTaskRequest):
    """创建任务，分析文件并生成计划"""
    from packages.agent_core.orchestrator import Orchestrator

    orchestrator = Orchestrator()

    # 启动任务
    task = orchestrator.start(request.file_path, request.user_input)

    # 分析并生成计划
    plan = orchestrator.analyze_and_plan(task.task_id)

    # 存储 orchestrator
    _orchestrators[task.task_id] = orchestrator

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "plan_display": orchestrator.get_plan_display(task.task_id),
        "needs_confirmation": plan.needs_confirmation(),
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    """查询任务状态"""
    orchestrator = _orchestrators.get(task_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Task not found")

    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
        "error": task.error_message,
    }


@router.post("/{task_id}/confirm")
async def confirm_task(task_id: str, request: ConfirmTaskRequest):
    """确认或拒绝执行计划"""
    orchestrator = _orchestrators.get(task_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Task not found")

    if not request.confirmed:
        return {"status": "rejected", "message": "Plan rejected by user"}

    # 确认并执行
    orchestrator.confirm(task_id)
    result = orchestrator.execute(task_id)

    return {
        "status": "done" if result["success"] else "failed",
        "result": result,
    }


@router.get("/{task_id}/audit")
async def get_audit_log(task_id: str):
    """获取任务审计日志"""
    orchestrator = _orchestrators.get(task_id)
    if not orchestrator:
        raise HTTPException(status_code=404, detail="Task not found")

    audit_log = orchestrator.get_audit_log(task_id)
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return audit_log.model_dump()
