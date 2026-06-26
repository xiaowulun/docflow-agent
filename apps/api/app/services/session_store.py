"""
Session Store - 会话存储

内存存储会话数据。接口设计成仓储模式，
后续切换到 SQLite（复用 config.sqlite_path）只需替换实现，不改调用方。

后续 SQLite 接入点：
- create/get/list/delete/rename 的方法签名保持不变
- 内部把 self._sessions: dict 换成 SQLAlchemy 的 session 查询即可
"""

import threading

from packages.schemas.conversation import Session


class SessionStore:
    """会话存储（线程安全的内存实现）"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, session: Session) -> Session:
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def list_all(self) -> list[Session]:
        """按更新时间倒序返回"""
        with self._lock:
            sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def update(self, session_id: str) -> Session | None:
        """更新时间戳并返回（已有 session 修改后调用）"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session


# 全局单例
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """获取全局 SessionStore 单例"""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
