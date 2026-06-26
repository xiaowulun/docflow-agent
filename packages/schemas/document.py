"""
内容对象数据模型

定义 pi agent 使用的通用文档对象。
第一版先聚焦纯文本内容，不绑定 Office/PDF 格式。
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
<<<<<<< HEAD
    """会话内的通用内容对象/草稿"""
=======
    """会话内的通用内容对象"""
>>>>>>> origin/main

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    session_id: str
    title: str
    content: str
    content_type: str = "text"
<<<<<<< HEAD
    output_format: str = "md"
    is_saved: bool = False
    file_path: str | None = None
=======
>>>>>>> origin/main
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()
