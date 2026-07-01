"""
文件信息数据模型

描述上传文件的元信息和分析结果。
"""

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class FileType(StrEnum):
    """支持的文件类型"""

    WORD = "word"
    EXCEL = "excel"
    PDF = "pdf"
    UNKNOWN = "unknown"


class FileInfo(BaseModel):
    """文件元信息"""

    file_id: str = Field(default_factory=lambda: uuid4().hex)
    filename: str
    file_type: FileType
    file_path: str  # 存储路径
    size_bytes: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_path(cls, path: str | Path) -> "FileInfo":
        """从文件路径创建 FileInfo"""
        p = Path(path)
        suffix = p.suffix.lower()
        type_map = {
            ".docx": FileType.WORD,
            ".doc": FileType.WORD,
            ".xlsx": FileType.EXCEL,
            ".xls": FileType.EXCEL,
            ".pdf": FileType.PDF,
        }
        return cls(
            filename=p.name,
            file_type=type_map.get(suffix, FileType.UNKNOWN),
            file_path=str(p),
            size_bytes=p.stat().st_size if p.exists() else 0,
        )


class FileAnalysis(BaseModel):
    """文件分析结果（Analyzer 输出）"""

    file_info: FileInfo
    text_content: str = ""  # 提取的文本内容
    structure: dict = Field(default_factory=dict)  # 文档结构（标题、段落等）
    fields_found: list[str] = Field(default_factory=list)  # 发现的可填充字段
    anchors: list[str] = Field(default_factory=list)  # 锚点位置
    page_count: int = 0  # 页数（PDF/Word）
    sheet_names: list[str] = Field(default_factory=list)  # Excel 工作表名
    metadata: dict = Field(default_factory=dict)  # 其他元数据
    ambiguities: list[str] = Field(default_factory=list)  # 需要人工消解的歧义
