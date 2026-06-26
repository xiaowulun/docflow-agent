"""
Document Store - 内容对象存储

第一版使用线程安全的内存实现，按会话维度管理文档。
后续可平滑切换到 SQLite 或其他持久化方案。
"""

import threading

from packages.schemas.document import Document


class DocumentStore:
    """内容对象存储（线程安全的内存实现）"""

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._lock = threading.Lock()

    def create(self, document: Document) -> Document:
        with self._lock:
            self._documents[document.id] = document
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
            return document


_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """获取全局 DocumentStore 单例"""
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store
