"""
pi agent 内置工具集

第一版聚焦会话内草稿管理与显式保存。
生成和编辑先写入草稿，只有在用户确认后才调用保存工具落盘。
"""

from contextvars import ContextVar, Token
from pathlib import Path
import re

from apps.api.app.services.document_store import get_document_store
from config import settings
from packages.schemas.document import Document

_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar(
    "current_session_id", default=None
)


list_contents_schema = {
    "type": "function",
    "function": {
        "name": "list_contents",
        "description": "列出当前会话里的所有草稿和已保存内容。当用户提到刚才那份、已有内容或内容列表时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


read_content_schema = {
    "type": "function",
    "function": {
        "name": "read_content",
        "description": "读取一份已有内容的完整正文和元信息。当需要查看、引用或修改已有内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "content_id": {
                    "type": "string",
                    "description": "要读取的内容 ID",
                }
            },
            "required": ["content_id"],
        },
    },
}


write_content_schema = {
    "type": "function",
    "function": {
        "name": "write_content",
        "description": "把一份新生成的正文写入当前会话草稿。生成新内容后先调用它保存草稿，但不要自动保存成文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "内容标题",
                },
                "content": {
                    "type": "string",
                    "description": "完整正文内容",
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


edit_content_schema = {
    "type": "function",
    "function": {
        "name": "edit_content",
        "description": "更新一份已有草稿的完整正文。当用户要求润色、扩写、改写或重写已有内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "content_id": {
                    "type": "string",
                    "description": "要更新的内容 ID",
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
            "required": ["content_id", "content"],
        },
    },
}


save_content_schema = {
    "type": "function",
    "function": {
        "name": "save_content",
        "description": "把一份已有草稿保存为文件。只有用户明确同意保存时才调用；未指定格式时默认使用 md。",
        "parameters": {
            "type": "object",
            "properties": {
                "content_id": {
                    "type": "string",
                    "description": "要保存的内容 ID",
                },
                "format": {
                    "type": "string",
                    "description": "保存格式，支持 md 或 txt，默认 md",
                },
                "filename": {
                    "type": "string",
                    "description": "可选，自定义文件名，不需要带扩展名",
                },
            },
            "required": ["content_id"],
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


def list_contents() -> dict:
    """列出当前会话下的所有内容对象"""
    session_id = _require_session_id()
    store = get_document_store()
    documents = store.list_by_session(session_id)
    return {
        "count": len(documents),
        "contents": [_serialize_content_summary(doc) for doc in documents],
    }


def read_content(content_id: str) -> dict:
    """读取指定内容对象"""
    content = _get_session_content(content_id)
    if content is None:
        return {"error": f"内容不存在: {content_id}"}

    return _serialize_content_detail(content)


def write_content(
    title: str,
    content: str,
    content_type: str = "text",
) -> dict:
    """创建新的会话草稿"""
    session_id = _require_session_id()
    store = get_document_store()
    document = Document(
        session_id=session_id,
        title=title.strip() or "未命名内容",
        content=content,
        content_type=content_type or "text",
    )
    store.create(document)
    detail = _serialize_content_detail(document)
    detail["message"] = "草稿已写入"
    return detail


def edit_content(
    content_id: str,
    content: str,
    title: str | None = None,
) -> dict:
    """更新已有草稿"""
    existing = _get_session_content(content_id)
    if existing is None:
        return {"error": f"内容不存在: {content_id}"}

    store = get_document_store()
    updated = store.update(content_id, content=content, title=title)
    if updated is None:
        return {"error": f"内容更新失败: {content_id}"}

    detail = _serialize_content_detail(updated)
    detail["message"] = "草稿已更新"
    return detail


def save_content(
    content_id: str,
    format: str = "md",
    filename: str | None = None,
) -> dict:
    """将草稿保存成文件"""
    content = _get_session_content(content_id)
    if content is None:
        return {"error": f"内容不存在: {content_id}"}

    fmt = (format or "md").lower().strip()
    if fmt not in {"md", "txt"}:
        return {"error": f"暂不支持的保存格式: {fmt}"}

    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename or content.title or "untitled")
    output_path = _next_available_path(output_dir, safe_name, fmt)
    output_path.write_text(content.content, encoding="utf-8")

    store = get_document_store()
    updated = store.mark_saved(
        content_id,
        output_format=fmt,
        file_path=str(output_path),
    )
    if updated is None:
        return {"error": f"保存状态更新失败: {content_id}"}

    return {
        "id": updated.id,
        "title": updated.title,
        "format": fmt,
        "file_path": updated.file_path,
        "message": f"内容已保存为 {fmt} 文件",
    }


def _get_session_content(content_id: str) -> Document | None:
    session_id = _require_session_id()
    store = get_document_store()
    content = store.get(content_id)
    if content is None or content.session_id != session_id:
        return None
    return content


def _serialize_content_summary(content: Document) -> dict:
    return {
        "id": content.id,
        "title": content.title,
        "content_type": content.content_type,
        "is_saved": content.is_saved,
        "output_format": content.output_format,
        "file_path": content.file_path,
        "updated_at": content.updated_at.isoformat(),
    }


def _serialize_content_detail(content: Document) -> dict:
    detail = _serialize_content_summary(content)
    detail.update(
        {
            "content": content.content,
            "created_at": content.created_at.isoformat(),
        }
    )
    return detail


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return cleaned or "untitled"


def _next_available_path(output_dir: Path, stem: str, fmt: str) -> Path:
    output_path = output_dir / f"{stem}.{fmt}"
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"{stem}_{counter}.{fmt}"
        counter += 1
    return output_path


BUILTIN_TOOLS = [
    list_contents_schema,
    read_content_schema,
    write_content_schema,
    edit_content_schema,
    save_content_schema,
]


BUILTIN_TOOL_FUNCS = {
    "list_contents": list_contents,
    "read_content": read_content,
    "write_content": write_content,
    "edit_content": edit_content,
    "save_content": save_content,
}


def get_tool_schemas() -> list[dict]:
    """返回所有工具的 schema（供 LLM 使用）"""
    return BUILTIN_TOOLS


def get_tool_func(name: str):
    """根据工具名获取执行函数"""
    return BUILTIN_TOOL_FUNCS.get(name)
