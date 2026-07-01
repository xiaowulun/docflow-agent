"""
Document Store - 内容对象存储

使用 JSON 文件持久化文档索引，避免进程重启后列表丢失。
"""

import json
import threading
from pathlib import Path

from packages.schemas.document import Document


_DOCUMENTS_FILE = Path("storage/documents.json")


class DocumentStore:
    """内容对象存储（JSON 文件持久化，线程安全）"""

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or _DOCUMENTS_FILE
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._documents: dict[str, Document] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _load_all(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            items = data.get("documents", []) if isinstance(data, dict) else data
            for item in items:
                document = Document(**item)
                self._documents[document.id] = document
        except Exception:
            self._documents = {}

    def _save_all(self) -> None:
        payload = {
            "documents": [doc.model_dump(mode="json") for doc in self._documents.values()]
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_path(file_path: str) -> str:
        return str(Path(file_path).expanduser().resolve())

    def create(self, document: Document) -> Document:
        with self._lock:
            if document.file_path:
                document.file_path = self._normalize_path(document.file_path)
            self._documents[document.id] = document
            self._save_all()
        return document

    def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

    def list_by_session(self, session_id: str) -> list[Document]:
        with self._lock:
            documents = [
                doc
                for doc in self._documents.values()
                if doc.session_id == session_id
            ]
        documents.sort(key=lambda d: d.updated_at, reverse=True)
        return documents

    def update(
        self,
        document_id: str,
        content: str,
        title: str | None = None,
    ) -> Document | None:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                return None
            document.content = content
            if title is not None:
                document.title = title
            document.touch()
            self._save_all()
            return document

    def mark_saved(
        self,
        document_id: str,
        *,
        output_format: str,
        file_path: str,
    ) -> Document | None:
        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                return None
            document.output_format = output_format
            document.file_path = self._normalize_path(file_path)
            document.is_saved = True
            document.touch()
            self._save_all()
            return document

    def upsert_file_document(
        self,
        *,
        session_id: str,
        title: str,
        content: str,
        content_type: str,
        output_format: str,
        file_path: str,
        is_saved: bool = True,
    ) -> Document:
        normalized_path = self._normalize_path(file_path)
        with self._lock:
            document = next(
                (
                    doc
                    for doc in self._documents.values()
                    if doc.session_id == session_id and doc.file_path == normalized_path
                ),
                None,
            )
            if document is None:
                document = Document(
                    session_id=session_id,
                    title=title,
                    content=content,
                    content_type=content_type,
                    output_format=output_format,
                    is_saved=is_saved,
                    file_path=normalized_path,
                )
                self._documents[document.id] = document
            else:
                document.title = title
                document.content = content
                document.content_type = content_type
                document.output_format = output_format
                document.is_saved = is_saved
                document.file_path = normalized_path
                document.touch()
            self._save_all()
            return document


_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """获取全局 DocumentStore 单例"""
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store
