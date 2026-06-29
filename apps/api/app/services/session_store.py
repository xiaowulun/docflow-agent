"""
Session Store - 会话存储

JSON 文件持久化存储。每个会话一个 JSON 文件，
重启不丢失数据。
"""

import json
import threading
from pathlib import Path

from packages.schemas.conversation import Session


_SESSIONS_DIR = Path("storage/sessions")


class SessionStore:
    """会话存储（JSON 文件持久化，线程安全）"""

    def __init__(self):
        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _session_file(self, session_id: str) -> Path:
        return _SESSIONS_DIR / f"{session_id}.json"

    def _load_all(self):
        for f in _SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                session = Session(**data)
                self._sessions[session.id] = session
            except Exception:
                pass

    def _save(self, session: Session):
        self._session_file(session.id).write_text(
            session.model_dump_json(), encoding="utf-8"
        )

    def create(self, session: Session) -> Session:
        with self._lock:
            self._sessions[session.id] = session
            self._save(session)
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def list_all(self) -> list[Session]:
        with self._lock:
            sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if self._sessions.pop(session_id, None) is not None:
                self._session_file(session_id).unlink(missing_ok=True)
                return True
            return False

    def update(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
                self._save(session)
            return session


# 全局单例
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
