"""
Task Service - 任务业务逻辑

封装任务相关的业务逻辑，供路由层调用。
后续可接入 SQLite 持久化。
"""

from packages.agent_core.orchestrator import Orchestrator
from packages.schemas.task import Task, TaskStatus


class TaskService:
    """任务服务"""

    def __init__(self):
        self._orchestrators: dict[str, Orchestrator] = {}

    def create_and_plan(self, file_path: str, user_input: str) -> dict:
        """创建任务并生成计划"""
        orchestrator = Orchestrator()
        task = orchestrator.start(file_path, user_input)
        plan = orchestrator.analyze_and_plan(task.task_id)

        self._orchestrators[task.task_id] = orchestrator

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "plan_display": orchestrator.get_plan_display(task.task_id),
            "needs_confirmation": plan.needs_confirmation(),
            "confirmation_request": (
                task.confirmation_request.model_dump()
                if task.confirmation_request
                else None
            ),
        }

    def confirm_and_execute(
        self,
        task_id: str,
        confirmed: bool,
        user_input: str | None = None,
    ) -> dict:
        """确认并执行任务"""
        orchestrator = self._orchestrators.get(task_id)
        if not orchestrator:
            raise ValueError(f"Task {task_id} not found")

        if not confirmed:
            confirmation_request = orchestrator.reject_confirmation(task_id)
            task = orchestrator.get_task(task_id)
            return {
                "task_id": task_id,
                "status": "rejected",
                "plan_display": orchestrator.get_plan_display(task_id),
                "error": task.error_message if task else None,
                "confirmation_request": (
                    confirmation_request.model_dump()
                    if confirmation_request
                    else None
                ),
            }

        confirmed_request = orchestrator.confirm(task_id)
        task = orchestrator.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        if (
            confirmed_request
            and confirmed_request.kind == "ambiguity_resolution"
        ):
            plan = orchestrator.resume(task_id, user_input=user_input)
            resumed_task = orchestrator.get_task(task_id)
            if resumed_task is None:
                raise ValueError(f"Task {task_id} not found")
            return {
                "task_id": task_id,
                "status": resumed_task.status.value,
                "message": "Ambiguity resolved, task replanned.",
                "plan_display": orchestrator.get_plan_display(task_id),
                "error": resumed_task.error_message,
                "needs_confirmation": plan.needs_confirmation(),
                "confirmation_request": (
                    resumed_task.confirmation_request.model_dump()
                    if resumed_task.confirmation_request
                    else None
                ),
            }

        if task.status != TaskStatus.EXECUTING:
            return {
                "task_id": task_id,
                "status": task.status.value,
                "plan_display": orchestrator.get_plan_display(task_id),
                "error": task.error_message,
                "confirmation_request": (
                    task.confirmation_request.model_dump()
                    if task.confirmation_request
                    else None
                ),
            }

        result = orchestrator.execute(task_id)
        finished_task = orchestrator.get_task(task_id)

        return {
            "task_id": task_id,
            "status": "done" if result["success"] else "failed",
            "plan_display": orchestrator.get_plan_display(task_id),
            "error": finished_task.error_message if finished_task else None,
            "result": result,
        }

    def get_task(self, task_id: str) -> Task | None:
        """获取任务"""
        orchestrator = self._orchestrators.get(task_id)
        if not orchestrator:
            return None
        return orchestrator.get_task(task_id)

    def get_audit_log(self, task_id: str):
        """获取任务审计日志"""
        orchestrator = self._orchestrators.get(task_id)
        if not orchestrator:
            return None
        return orchestrator.get_audit_log(task_id)


_task_service: TaskService | None = None


def get_task_service() -> TaskService:
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
