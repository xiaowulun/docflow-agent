"""
依赖注入

FastAPI 的依赖项定义。
"""

from apps.api.app.services.task_service import TaskService

# 全局单例
_task_service: TaskService | None = None


def get_task_service() -> TaskService:
    """获取 TaskService 单例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
