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

    IDLE = "idle"  # 空闲，等待用户输入
    THINKING = "thinking"  # 正在调用 LLM 思考
    CALLING_TOOL = "calling_tool"  # 正在执行工具
    ERROR = "error"  # 出错


class ToolCallInfo(BaseModel):
    """LLM 发起的工具调用记录（用于展示）"""

    id: str = ""  # OpenAI 返回的 tool_call id，用于关联 tool 消息
    name: str
    arguments: dict


class Message(BaseModel):
    """单条对话消息

    兼容 OpenAI message 格式，同时额外存储用于展示的字段。
    """

    role: str  # user / assistant / tool
    content: str = ""
    # assistant 消息可能携带工具调用
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    # tool 消息需要标记是哪个工具的返回
    tool_name: str | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class ToolInfo(BaseModel):
    """工具元信息（用于展示给前端）"""

    name: str
    description: str


class Session(BaseModel):
    """对话会话"""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str = "新会话"
    status: SessionStatus = SessionStatus.IDLE
    model: str = ""  # 当前使用的模型名
    messages: list[Message] = Field(default_factory=list)
    tools: list[ToolInfo] = Field(default_factory=list)  # 可用工具列表
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()
