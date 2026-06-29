"""
对话 API 路由

提供会话管理 + 发消息（驱动 agent 循环）的接口。
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.app.services.document_store import get_document_store
from apps.api.app.services.session_store import get_session_store
from config import settings
from packages.agent_core.conversation import ConversationAgent
from packages.schemas.conversation import Session, SessionStatus

router = APIRouter()


_agent: ConversationAgent | None = None


def get_agent() -> ConversationAgent:
    global _agent
    if _agent is None:
        _agent = ConversationAgent()
    return _agent


class CreateSessionRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    content: str
    file_ids: list[str] = []  # 关联的文件 ID（可选）


class RenameSessionRequest(BaseModel):
    title: str


@router.post("/sessions")
async def create_session(req: CreateSessionRequest | None = None):
    """新建会话"""
    agent = get_agent()
    store = get_session_store()

    session = Session(
        title=req.title if req and req.title else "新会话",
        model=settings.llm_model,
        tools=agent.get_available_tools(),
    )
    store.create(session)

    return _session_detail(session)


@router.get("/sessions")
async def list_sessions():
    """会话列表（左侧栏用，只返回 id 和 title）"""
    store = get_session_store()
    sessions = store.list_all()
    return [{"id": s.id, "title": s.title} for s in sessions]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取单个会话详情（含消息历史）"""
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _session_detail(session)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    store = get_session_store()
    deleted = store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"deleted": True}


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameSessionRequest):
    """重命名会话"""
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = req.title
    store.update(session_id)
    return _session_detail(session)


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, req: SendMessageRequest):
    """发消息（驱动 agent 循环）

    这是核心接口：
    1. 取出会话
    2. 调 agent.chat() 执行 think→act→observe 循环
    3. 返回 assistant 的最终回复

    注意：消息历史和工具调用过程都记录在 session.messages 里，
    前端可通过 GET /sessions/{id} 拉取完整过程。
    """
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if not req.content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    agent = get_agent()

    try:
        reply = agent.chat(session, req.content.strip())
    except Exception as e:
        session.status = SessionStatus.ERROR
        store.update(session_id)
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {e}")

    store.update(session_id)

    return {"reply": reply}


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(session_id: str, req: SendMessageRequest):
    """流式发消息（SSE）

    返回 Server-Sent Events 流，每个事件包含：
    - 文本块：{"type": "text", "content": "..."}
    - 工具调用：{"type": "tool_call", "tools": ["..."]}
    - 工具结果：{"type": "tool_result", "name": "...", "result": {...}}
    - 完成：{"type": "done"}
    """
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if not req.content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    agent = get_agent()

    # 获取文件内容和文件信息（如果有）
    file_context = ""
    file_info = []
    if req.file_ids:
        from apps.api.app.services.file_store import get_file_store
        file_store = get_file_store()
        for file_id in req.file_ids:
            record = file_store.get_file(file_id)
            if record:
                # 收集文件信息用于前端显示
                file_info.append({
                    "id": record.id,
                    "filename": record.original_name,
                    "file_type": record.file_type,
                    "extension": record.extension,
                    "size_bytes": record.size_bytes,
                })
                # 收集文件内容用于 LLM 上下文
                if record.file_type == "image":
                    file_context += f"\n[图片: {record.original_name}]\n"
                elif record.extracted_text:
                    file_context += f"\n[文件: {record.original_name}]\n{record.extracted_text}\n"

    def event_generator():
        try:
            for chunk in agent.chat_stream(session, req.content.strip(), file_context, file_info=file_info):
                if chunk == "\0DONE\0":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                elif chunk.startswith("\0TOOL_CALL_START:"):
                    tools_str = chunk[17:-1]
                    yield f"data: {json.dumps({'type': 'tool_call', 'tools': json.loads(tools_str)})}\n\n"
                elif chunk.startswith("\0TOOL_RESULT:"):
                    parts = chunk[13:-1].split(":", 1)
                    tool_name = parts[0]
                    result = json.loads(parts[1])
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': tool_name, 'result': result})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                store.update(session_id)
        except Exception as e:
            session.status = SessionStatus.ERROR
            store.update(session_id)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _session_detail(session: Session) -> dict:
    """把 Session 序列化成前端需要的结构"""
    document_store = get_document_store()
    contents = document_store.list_by_session(session.id)
    return {
        "id": session.id,
        "title": session.title,
        "status": session.status.value,
        "model": session.model,
        "messages": [m.model_dump() for m in session.messages],
        "tools": [t.model_dump() for t in session.tools],
        "contents": [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "content_type": item.content_type,
                "output_format": item.output_format,
                "is_saved": item.is_saved,
                "file_path": item.file_path,
                "createdAt": item.created_at.isoformat(),
                "updatedAt": item.updated_at.isoformat(),
            }
            for item in contents
        ],
        "createdAt": session.created_at.isoformat(),
        "updatedAt": session.updated_at.isoformat(),
    }
