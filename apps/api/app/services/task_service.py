"""
Task Service - 任务业务逻辑

封装任务相关的业务逻辑，供路由层调用。
后续可接入 SQLite 持久化。
"""

from packages.agent_core.orchestrator import Orchestrator
from packages.schemas.task import Task


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
        }

    def confirm_and_execute(self, task_id: str, confirmed: bool) -> dict:
        """确认并执行任务"""
        orchestrator = self._orchestrators.get(task_id)
        if not orchestrator:
            raise ValueError(f"Task {task_id} not found")

        if not confirmed:
            return {"status": "rejected"}

        orchestrator.confirm(task_id)
        result = orchestrator.execute(task_id)

        return {
            "status": "done" if result["success"] else "failed",
            "result": result,
        }

    def get_task(self, task_id: str) -> Task | None:
        """获取任务"""
        orchestrator = self._orchestrators.get(task_id)
        if not orchestrator:
            return None
        return orchestrator.get_task(task_id)
