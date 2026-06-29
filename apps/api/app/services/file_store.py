"""
文件存储管理

管理上传文件的元数据和内容提取。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel

from config import settings


class FileRecord(BaseModel):
    """上传文件记录"""
    id: str
    filename: str
    original_name: str
    file_path: str
    file_type: str  # image / document
    extension: str
    size_bytes: int
    extracted_text: Optional[str] = None
    created_at: datetime = datetime.now()


class FileStore:
    """文件存储管理器"""

    def __init__(self):
        self.storage_dir = settings.upload_dir
        self.meta_file = self.storage_dir / "files_meta.json"
        self.files: dict[str, FileRecord] = {}
        self._load_meta()

    def _load_meta(self):
        """加载元数据"""
        if self.meta_file.exists():
            try:
                data = json.loads(self.meta_file.read_text(encoding="utf-8"))
                self.files = {k: FileRecord(**v) for k, v in data.items()}
            except Exception:
                self.files = {}

    def _save_meta(self):
        """保存元数据"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        data = {}
        for k, v in self.files.items():
            d = v.model_dump()
            # datetime 转 ISO 字符串
            if isinstance(d.get("created_at"), datetime):
                d["created_at"] = d["created_at"].isoformat()
            data[k] = d
        self.meta_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_file(self, original_name: str, file_content: bytes) -> FileRecord:
        """保存上传文件"""
        from apps.api.app.services.file_extractor import IMAGE_EXTENSIONS, DOCUMENT_EXTENSIONS

        ext = Path(original_name).suffix.lower()
        file_id = uuid4().hex[:12]
        saved_name = f"{file_id}_{original_name}"
        file_path = self.storage_dir / saved_name

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_content)

        file_type = "image" if ext in IMAGE_EXTENSIONS else "document"

        # 提取文本内容（仅文档类型）
        extracted_text = None
        if file_type == "document":
            from apps.api.app.services.file_extractor import extract_text
            extracted_text = extract_text(file_path)

        record = FileRecord(
            id=file_id,
            filename=saved_name,
            original_name=original_name,
            file_path=str(file_path),
            file_type=file_type,
            extension=ext,
            size_bytes=len(file_content),
            extracted_text=extracted_text,
        )

        self.files[file_id] = record
        self._save_meta()
        return record

    def get_file(self, file_id: str) -> Optional[FileRecord]:
        """获取文件记录"""
        return self.files.get(file_id)

    def list_files(self) -> list[FileRecord]:
        """列出所有文件"""
        return list(self.files.values())

    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        record = self.files.get(file_id)
        if not record:
            return False

        # 删除物理文件
        file_path = Path(record.file_path)
        if file_path.exists():
            file_path.unlink()

        # 删除记录
        del self.files[file_id]
        self._save_meta()
        return True


# 全局单例
_file_store: Optional[FileStore] = None


def get_file_store() -> FileStore:
    global _file_store
    if _file_store is None:
        _file_store = FileStore()
    return _file_store
