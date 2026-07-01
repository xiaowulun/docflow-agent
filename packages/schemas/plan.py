"""
执行计划数据模型

Planner 生成结构化计划，描述要执行的操作列表。
每一步是一个 Action，包含工具名和参数。
"""

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    """操作类型"""

    READ = "read"  # 只读操作
    WRITE = "write"  # 写入操作（需要确认）
    EXPORT = "export"  # 导出操作（需要确认）


class Action(BaseModel):
    """单个执行步骤"""

    action_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    tool_name: str  # 对应 registry 中注册的工具名
    action_type: ActionType
    description: str  # 人类可读的描述
    params: dict = Field(default_factory=dict)  # 工具参数
    requires_confirmation: bool = True  # 写入/导出操作必须确认


class ExecutionPlan(BaseModel):
    """执行计划"""

    plan_id: str = Field(default_factory=lambda: uuid4().hex)
    task_id: str
    intent: str  # 用户意图的结构化描述
    actions: list[Action] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)  # 不确定项
    expected_output: str = ""  # 预期输出描述

    def get_confirmation_required_actions(self) -> list[Action]:
        """获取所有需要用户确认的步骤"""
        return [a for a in self.actions if a.requires_confirmation]

    def get_writable_actions(self) -> list[Action]:
        """获取所有需要写入的操作"""
        return [a for a in self.actions if a.action_type in (ActionType.WRITE, ActionType.EXPORT)]

    def needs_confirmation(self) -> bool:
        """是否需要用户确认"""
        return bool(self.uncertainties) or any(a.requires_confirmation for a in self.actions)
