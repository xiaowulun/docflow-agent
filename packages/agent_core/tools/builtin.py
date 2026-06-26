"""
pi agent 内置工具集

第一版聚焦通用内容对象，不绑定 Office 或编程场景。
工具负责读写持久化，内容生成与改写由 LLM 完成。
"""

from contextvars import ContextVar, Token

from apps.api.app.services.document_store import get_document_store
from packages.schemas.document import Document

_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar(
    "current_session_id", default=None
)


list_documents_schema = {
    "type": "function",
    "function": {
        "name": "list_documents",
        "description": "列出当前会话里的所有内容对象。当用户提到刚才那份、已有文档、当前内容列表时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


read_document_schema = {
    "type": "function",
    "function": {
        "name": "read_document",
        "description": "读取一份已有内容对象的完整内容和元信息。当需要查看、引用或修改已有内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "要读取的文档 ID",
                }
            },
            "required": ["document_id"],
        },
    },
}


create_document_schema = {
    "type": "function",
    "function": {
        "name": "create_document",
        "description": "创建一份新的内容对象。当你已经生成好用户需要的正文后，用它保存内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "文档标题",
                },
                "content": {
                    "type": "string",
                    "description": "要保存的正文内容",
                },
                "content_type": {
                    "type": "string",
                    "description": "内容类型，例如 text、note、summary、draft",
                },
            },
            "required": ["title", "content"],
        },
    },
}


update_document_schema = {
    "type": "function",
    "function": {
        "name": "update_document",
        "description": "更新一份已有内容对象，相当于编辑和覆写。当用户要求修改、润色、扩写或重写已有内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "要更新的文档 ID",
                },
                "content": {
                    "type": "string",
                    "description": "更新后的完整正文",
                },
                "title": {
                    "type": "string",
                    "description": "可选，更新后的标题",
                },
            },
            "required": ["document_id", "content"],
        },
    },
}


def set_current_session_id(session_id: str) -> Token:
    """设置当前工具调用的会话上下文"""
    return _CURRENT_SESSION_ID.set(session_id)


def reset_current_session_id(token: Token) -> None:
    """重置当前工具调用的会话上下文"""
    _CURRENT_SESSION_ID.reset(token)


def _require_session_id() -> str:
    session_id = _CURRENT_SESSION_ID.get()
    if not session_id:
        raise RuntimeError("当前工具调用缺少会话上下文")
    return session_id


def list_documents() -> dict:
    """列出当前会话下的所有内容对象"""
    session_id = _require_session_id()
    store = get_document_store()
    documents = store.list_by_session(session_id)
    return {
        "count": len(documents),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "content_type": doc.content_type,
                "updated_at": doc.updated_at.isoformat(),
            }
            for doc in documents
        ],
    }


def read_document(document_id: str) -> dict:
    """读取指定内容对象"""
    session_id = _require_session_id()
    store = get_document_store()
    document = store.get(document_id)
    if document is None or document.session_id != session_id:
        return {"error": f"文档不存在: {document_id}"}

    return {
        "id": document.id,
        "title": document.title,
        "content": document.content,
        "content_type": document.content_type,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def create_document(
    title: str,
    content: str,
    content_type: str = "text",
) -> dict:
    """创建新的内容对象"""
    session_id = _require_session_id()
    store = get_document_store()
    document = Document(
        session_id=session_id,
        title=title.strip() or "未命名文档",
        content=content,
        content_type=content_type or "text",
    )
    store.create(document)
    return {
        "id": document.id,
        "title": document.title,
        "content": document.content,
        "content_type": document.content_type,
        "message": "文档已创建",
    }


def update_document(
    document_id: str,
    content: str,
    title: str | None = None,
) -> dict:
    """更新已有内容对象"""
    session_id = _require_session_id()
    store = get_document_store()
    document = store.get(document_id)
    if document is None or document.session_id != session_id:
        return {"error": f"文档不存在: {document_id}"}

    updated = store.update(document_id, content=content, title=title)
    if updated is None:
        return {"error": f"文档更新失败: {document_id}"}

    return {
        "id": updated.id,
        "title": updated.title,
        "content": updated.content,
        "content_type": updated.content_type,
        "message": "文档已更新",
    }


BUILTIN_TOOLS = [
    list_documents_schema,
    read_document_schema,
    create_document_schema,
    update_document_schema,
]


BUILTIN_TOOL_FUNCS = {
    "list_documents": list_documents,
    "read_document": read_document,
    "create_document": create_document,
    "update_document": update_document,
}


def get_tool_schemas() -> list[dict]:
    """返回所有工具的 schema（供 LLM 使用）"""
    return BUILTIN_TOOLS


def get_tool_func(name: str):
    """根据工具名获取执行函数"""
    return BUILTIN_TOOL_FUNCS.get(name)
