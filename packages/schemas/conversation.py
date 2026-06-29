"""
对话数据模型

定义对话型 agent 的会话和消息结构。
- Session: 一个对话会话（含历史消息、状态）
- Message: 单条消息（user/assistant/tool）
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """会话状态"""

    IDLE = "idle"
    THINKING = "thinking"
    CALLING_TOOL = "calling_tool"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SAVING = "saving"
    ERROR = "error"


class ToolCallInfo(BaseModel):
    """LLM 发起的工具调用记录（用于展示）"""

    id: str = ""
    name: str
    arguments: dict


class Message(BaseModel):
    """单条对话消息

    兼容 OpenAI message 格式，同时额外存储用于展示的字段。
    """

    role: str
    content: str = ""
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    tool_name: str | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)  # 存储文件信息等额外数据


class ToolInfo(BaseModel):
    """工具元信息（用于展示给前端）"""

    name: str
    description: str


class Session(BaseModel):
    """对话会话"""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str = "新会话"
    status: SessionStatus = SessionStatus.IDLE
    model: str = ""
    messages: list[Message] = Field(default_factory=list)
    tools: list[ToolInfo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()
