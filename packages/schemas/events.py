"""
审计事件数据模型

记录任务生命周期中的每个关键事件，用于调试和审计。
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """事件类型"""

    TASK_CREATED = "task_created"
    FILE_UPLOADED = "file_uploaded"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_DONE = "analysis_done"
    PLAN_GENERATED = "plan_generated"
    CONFIRMATION_REQUESTED = "confirmation_requested"
    CONFIRMATION_GIVEN = "confirmation_given"
    EXECUTION_STARTED = "execution_started"
    ACTION_EXECUTED = "action_executed"
    EXECUTION_DONE = "execution_done"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_DONE = "verification_done"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class AuditEvent(BaseModel):
    """单条审计事件"""

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    task_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    actor: str = "system"  # system / user
    detail: dict = Field(default_factory=dict)  # 事件附加数据
    error: str | None = None  # 如果是失败事件，记录错误信息


class TaskAuditLog(BaseModel):
    """任务完整审计日志"""

    task_id: str
    events: list[AuditEvent] = Field(default_factory=list)

    def add_event(self, event_type: EventType, actor: str = "system", **detail) -> AuditEvent:
        """添加事件"""
        event = AuditEvent(
            task_id=self.task_id,
            event_type=event_type,
            actor=actor,
            detail=detail,
        )
        self.events.append(event)
        return event

    def get_last_event(self) -> AuditEvent | None:
        """获取最后一个事件"""
        return self.events[-1] if self.events else None

    def has_error(self) -> bool:
        """是否有错误事件"""
        return any(e.error for e in self.events)
