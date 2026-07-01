"""
任务数据模型

定义任务状态机和任务实体。
状态流转：
created -> analyzing -> planned -> awaiting_confirm -> executing -> verifying -> done / failed
"""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    """任务状态枚举"""

    CREATED = "created"
    ANALYZING = "analyzing"
    PLANNED = "planned"
    AWAITING_CONFIRM = "awaiting_confirm"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"


class TaskType(StrEnum):
    """任务类型"""

    WORD_READ = "word_read"
    WORD_WRITE = "word_write"
    EXCEL_READ = "excel_read"
    EXCEL_WRITE = "excel_write"
    PDF_READ = "pdf_read"
    PDF_EXPORT = "pdf_export"
    UNKNOWN = "unknown"


class ConfirmationKind(StrEnum):
    """确认请求类型"""

    PLAN_REVIEW = "plan_review"
    RISKY_ACTION = "risky_action"
    AMBIGUITY_RESOLUTION = "ambiguity_resolution"


class ConfirmationStage(StrEnum):
    """确认发生的任务阶段"""

    ANALYZING = "analyzing"
    PLANNED = "planned"
    EXECUTING = "executing"


class ConfirmationRequest(BaseModel):
    """等待用户处理的确认请求"""

    request_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    kind: ConfirmationKind
    stage: ConfirmationStage
    message: str
    blocking: bool = True
    options: list[str] = Field(default_factory=lambda: ["approve", "reject"])
    details: dict = Field(default_factory=dict)
    resume_from: str | None = None


class Task(BaseModel):
    """任务实体"""

    task_id: str = Field(default_factory=lambda: uuid4().hex)
    task_type: TaskType = TaskType.UNKNOWN
    status: TaskStatus = TaskStatus.CREATED

    # 输入
    user_input: str = ""  # 用户的自然语言指令
    file_paths: list[str] = Field(default_factory=list)  # 上传的文件路径

    # 输出
    output_paths: list[str] = Field(default_factory=list)  # 生成的结果文件路径
    error_message: str | None = None
    confirmation_request: ConfirmationRequest | None = None

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_status(self, new_status: TaskStatus) -> None:
        """更新任务状态"""
        self.status = new_status
        self.updated_at = datetime.now()

    def set_confirmation_request(self, request: ConfirmationRequest | None) -> None:
        """设置或清空当前确认请求"""
        self.confirmation_request = request
        self.updated_at = datetime.now()
