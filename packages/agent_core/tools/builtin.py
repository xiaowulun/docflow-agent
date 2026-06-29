"""
pi agent 内置工具集

第一版聚焦会话内草稿管理与显式保存。
生成和编辑先写入草稿，只有在用户确认后才调用保存工具落盘。
"""

import re
from contextvars import ContextVar, Token
from pathlib import Path

from apps.api.app.services.document_store import get_document_store
from config import settings
from packages.schemas.document import Document
from packages.tooling.officecli.docx import (  # noqa: F401
    add_docx,
    batch_docx,
    clear_docx,
    create_docx,
    get_docx,
    move_docx,
    query_docx,
    raw_docx,
    raw_set_docx,
    remove_docx,
    replace_docx,
    set_docx,
    swap_docx,
    validate_docx,
    view_docx,
)
from packages.tooling.officecli.pptx import (  # noqa: F401
    add_pptx,
    add_pptx_slide_with_layout,
    batch_pptx,
    clear_pptx,
    create_pptx,
    get_pptx,
    merge_document,
    move_pptx,
    office_help,
    query_pptx,
    raw_pptx,
    raw_set_pptx,
    remove_pptx,
    replace_pptx,
    set_pptx,
    swap_pptx,
    validate_pptx,
    view_pptx,
)
from packages.tooling.officecli.schemas import OFFICECLI_SCHEMAS
from packages.tooling.officecli.session import (  # noqa: F401
    office_close,
    office_open,
    office_save,
)
from packages.tooling.officecli.xlsx import (  # noqa: F401
    add_xlsx,
    batch_xlsx,
    clear_xlsx,
    create_xlsx,
    get_xlsx,
    import_xlsx,
    move_xlsx,
    query_xlsx,
    raw_set_xlsx,
    raw_xlsx,
    remove_xlsx,
    replace_xlsx,
    set_xlsx,
    swap_xlsx,
    validate_xlsx,
    view_xlsx,
)

_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar("current_session_id", default=None)


list_contents_schema = {
    "type": "function",
    "function": {
        "name": "list_contents",
        "description": (
            "列出当前会话里的所有草稿和已保存内容。当用户提到刚才那份、已有内容或内容列表时使用。"
        ),
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
        "description": (
            "把一份新生成的正文写入当前会话草稿。生成新内容后先调用它保存草稿，但不要自动保存成文件。"
        ),
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
        "description": (
            "更新一份已有草稿的完整正文。当用户要求润色、扩写、改写或重写已有内容时使用。"
        ),
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
        "description": (
            "把一份已有草稿保存为文件。只有用户明确同意保存时才调用；未指定格式时默认使用 md。"
        ),
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


web_search_schema = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "联网搜索，获取最新的网页信息。当用户提问涉及实时资讯、新闻、价格、天气、"
            "或其他需要联网才能回答的问题时使用。返回搜索结果的标题、摘要和链接。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5",
                },
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str, max_results: int = 5) -> dict:
    """联网搜索，返回结构化的搜索结果"""
    api_key = settings.tavily_api_key
    if not api_key:
        return {"error": "未配置 TAVILY_API_KEY，无法使用搜索功能"}

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
            include_raw_content=False,
        )

        results = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                }
            )

        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        return {"error": f"搜索失败: {e}"}


generate_image_schema = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "根据文字描述生成图片。当用户要求生成图片、创建图像、绘制插图时使用。"
            "使用 Agnes 视觉模型，支持文生图功能。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "图片描述，用英文描述效果更佳",
                },
                "width": {
                    "type": "integer",
                    "description": "图片宽度（像素），默认 1024",
                },
                "height": {
                    "type": "integer",
                    "description": "图片高度（像素），默认 1024",
                },
                "filename": {
                    "type": "string",
                    "description": "可选，自定义文件名，不需要带扩展名",
                },
            },
            "required": ["prompt"],
        },
    },
}

analyze_image_schema = {
    "type": "function",
    "function": {
        "name": "analyze_image",
        "description": (
            "分析图片内容，提取图片中的文字、物体、场景等信息。"
            "当用户上传图片并要求分析、识别、提取信息时使用。"
            "使用 Agnes 视觉模型，支持多模态理解能力。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径",
                },
                "prompt": {
                    "type": "string",
                    "description": "可选，分析提示，例如 '这张图片中有什么？' 或 '提取图片中的文字'",
                },
            },
            "required": ["image_path"],
        },
    },
}


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    filename: str | None = None,
) -> dict:
    """使用 Agnes 模型生成图片"""
    api_key = settings.agnes_api_key
    base_url = settings.agnes_base_url
    model = settings.agnes_image_model

    if not api_key:
        return {"error": "未配置 AGNES_API_KEY，无法使用图片生成功能"}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)

        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=f"{width}x{height}",
            n=1,
        )

        if not response.data:
            return {"error": "图片生成失败：未返回数据"}

        image_url = response.data[0].url
        if not image_url:
            return {"error": "图片生成失败：未返回图片 URL"}

        # 下载图片并保存
        import httpx
        import time

        output_dir = settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _safe_filename(filename or f"image_{int(time.time())}")
        output_path = output_dir / f"{safe_name}.png"

        with httpx.Client() as http_client:
            img_response = http_client.get(image_url, timeout=60)
            img_response.raise_for_status()
            output_path.write_bytes(img_response.content)

        return {
            "prompt": prompt,
            "size": f"{width}x{height}",
            "file_path": str(output_path),
            "url": image_url,
            "message": f"图片已生成并保存为 {output_path.name}",
        }
    except Exception as e:
        return {"error": f"图片生成失败: {e}"}


def analyze_image(image_path: str, prompt: str = "描述这张图片的内容") -> dict:
    """使用 Agnes 视觉模型分析图片内容"""
    api_key = settings.agnes_api_key
    base_url = settings.agnes_base_url
    model = settings.agnes_vision_model

    if not api_key:
        return {"error": "未配置 AGNES_API_KEY，无法使用图片分析功能"}

    import base64
    from pathlib import Path

    image_file = Path(image_path)
    if not image_file.exists():
        return {"error": f"图片文件不存在: {image_path}"}

    try:
        # 读取图片并转换为 base64
        with open(image_file, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 确定图片 MIME 类型
        suffix = image_file.suffix.lower()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(suffix, "image/png")

        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                            },
                        },
                    ],
                }
            ],
        )

        if not response.choices:
            return {"error": "图片分析失败：未返回结果"}

        analysis = response.choices[0].message.content
        return {
            "image_path": image_path,
            "prompt": prompt,
            "analysis": analysis,
            "message": "图片分析完成",
        }
    except Exception as e:
        return {"error": f"图片分析失败: {e}"}


BUILTIN_TOOLS = [
    list_contents_schema,
    read_content_schema,
    write_content_schema,
    edit_content_schema,
    save_content_schema,
    web_search_schema,
    generate_image_schema,
    analyze_image_schema,
] + OFFICECLI_SCHEMAS


BUILTIN_TOOL_FUNCS = {
    "list_contents": list_contents,
    "read_content": read_content,
    "write_content": write_content,
    "edit_content": edit_content,
    "save_content": save_content,
    "web_search": web_search,
    "generate_image": generate_image,
    "analyze_image": analyze_image,
    # 基础工具
    "create_docx": create_docx,
    "create_xlsx": create_xlsx,
    "create_pptx": create_pptx,
    "add_pptx_slide_with_layout": add_pptx_slide_with_layout,
    "view_docx": view_docx,
    "view_xlsx": view_xlsx,
    "view_pptx": view_pptx,
    "get_docx": get_docx,
    "get_xlsx": get_xlsx,
    "get_pptx": get_pptx,
    "query_docx": query_docx,
    "query_xlsx": query_xlsx,
    "query_pptx": query_pptx,
    "set_docx": set_docx,
    "set_xlsx": set_xlsx,
    "set_pptx": set_pptx,
    "add_docx": add_docx,
    "add_xlsx": add_xlsx,
    "add_pptx": add_pptx,
    "remove_docx": remove_docx,
    "remove_xlsx": remove_xlsx,
    "remove_pptx": remove_pptx,
    "merge_document": merge_document,
    "office_help": office_help,
    # 位置控制
    "move_docx": move_docx,
    "move_xlsx": move_xlsx,
    "move_pptx": move_pptx,
    "swap_docx": swap_docx,
    "swap_xlsx": swap_xlsx,
    "swap_pptx": swap_pptx,
    # 原始 XML
    "raw_docx": raw_docx,
    "raw_xlsx": raw_xlsx,
    "raw_pptx": raw_pptx,
    "raw_set_docx": raw_set_docx,
    "raw_set_xlsx": raw_set_xlsx,
    "raw_set_pptx": raw_set_pptx,
    # 验证
    "validate_docx": validate_docx,
    "validate_xlsx": validate_xlsx,
    "validate_pptx": validate_pptx,
    # 批量操作
    "batch_docx": batch_docx,
    "batch_xlsx": batch_xlsx,
    "batch_pptx": batch_pptx,
    # 数据导入
    "import_xlsx": import_xlsx,
    # 驻留模式
    "office_open": office_open,
    "office_close": office_close,
    "office_save": office_save,
    # 清空和替换
    "clear_docx": clear_docx,
    "clear_xlsx": clear_xlsx,
    "clear_pptx": clear_pptx,
    "replace_docx": replace_docx,
    "replace_xlsx": replace_xlsx,
    "replace_pptx": replace_pptx,
}


def get_tool_schemas() -> list[dict]:
    """返回所有工具的 schema（供 LLM 使用）"""
    return BUILTIN_TOOLS


def get_tool_func(name: str):
    """根据工具名获取执行函数"""
    return BUILTIN_TOOL_FUNCS.get(name)
