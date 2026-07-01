"""
对话 API 路由

提供会话管理 + 发消息（驱动 agent 循环）的接口。
"""

import json
from time import perf_counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.app.services.document_store import get_document_store
from apps.api.app.services.file_store import get_file_store
from apps.api.app.services.session_store import get_session_store
from apps.api.app.services.task_service import get_task_service
from config import settings
from packages.agent_core.conversation import ConversationAgent
from packages.schemas.conversation import Message, Session, SessionStatus
from packages.schemas.task import ConfirmationKind

router = APIRouter()


DOC_TASK_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".pdf"}
APPROVE_WORDS = {"确认", "继续", "执行", "开始", "approve", "yes", "ok", "y"}
REJECT_WORDS = {"拒绝", "取消", "停止", "reject", "no", "n"}

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


class ConfirmSessionTaskRequest(BaseModel):
    confirmed: bool
    user_input: str | None = None


@router.post("/sessions")
async def create_session(req: CreateSessionRequest | None = None):
    """新建会话"""
    store = get_session_store()

    session = Session(
        title=req.title if req and req.title else "新会话",
        model=settings.llm_model,
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
    """发消息（驱动 agent 循环）"""
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    file_context, file_info, document_records = _load_uploaded_files(req.file_ids)

    try:
        task_message = _maybe_handle_task_message(
            session,
            content,
            file_info,
            document_records,
        )
        if task_message is not None:
            store.update(session_id)
            return {"reply": task_message.content, "message": task_message.model_dump()}

        agent = get_agent()
        reply = agent.chat(session, content)
    except Exception as exc:
        session.status = SessionStatus.ERROR
        store.update(session_id)
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {exc}") from exc

    store.update(session_id)
    return {"reply": reply}


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(session_id: str, req: SendMessageRequest):
    """流式发消息（SSE）"""
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    file_context, file_info, document_records = _load_uploaded_files(req.file_ids)

    if document_records:
        def task_generator():
            try:
                yield _sse({"type": "text", "content": "正在分析文档并生成执行计划..."})
                _maybe_handle_task_message(
                    session,
                    content,
                    file_info,
                    document_records,
                )
                store.update(session_id)
                yield _sse({"type": "done"})
            except Exception as exc:
                session.status = SessionStatus.ERROR
                store.update(session_id)
                yield _sse({"type": "error", "message": str(exc)})

        return StreamingResponse(
            task_generator(),
            media_type="text/event-stream",
            headers=_stream_headers(),
        )

    pending_task = _find_pending_task_event(session)
    is_ambiguity_follow_up = (
        pending_task is not None
        and pending_task.get("confirmation_request", {}).get("kind")
        == ConfirmationKind.AMBIGUITY_RESOLUTION.value
    )
    confirmation_intent = _parse_confirmation_intent(content)
    is_task_confirmation = pending_task is not None and confirmation_intent is not None

    if is_ambiguity_follow_up or is_task_confirmation:
        def task_generator():
            try:
                initial_text = (
                    "正在根据你的补充重新分析文档..."
                    if is_ambiguity_follow_up
                    else "正在继续处理文档任务..."
                )
                yield _sse({"type": "text", "content": initial_text})
                _maybe_handle_task_message(
                    session,
                    content,
                    file_info,
                    document_records,
                )
                store.update(session_id)
                yield _sse({"type": "done"})
            except Exception as exc:
                session.status = SessionStatus.ERROR
                store.update(session_id)
                yield _sse({"type": "error", "message": str(exc)})

        return StreamingResponse(
            task_generator(),
            media_type="text/event-stream",
            headers=_stream_headers(),
        )

    agent = get_agent()

    def event_generator():
        try:
            for chunk in agent.chat_stream(
                session,
                content,
                file_context,
                file_info=file_info,
            ):
                if chunk == "\0DONE\0":
                    yield _sse({"type": "done"})
                elif chunk.startswith("\0TOOL_CALL_START:"):
                    tools_str = chunk[17:-1]
                    yield _sse(
                        {"type": "tool_call", "tools": json.loads(tools_str)}
                    )
                elif chunk.startswith("\0TOOL_RESULT:"):
                    parts = chunk[13:-1].split(":", 1)
                    tool_name = parts[0]
                    result = json.loads(parts[1])
                    yield _sse(
                        {"type": "tool_result", "name": tool_name, "result": result}
                    )
                else:
                    yield _sse({"type": "text", "content": chunk})
                store.update(session_id)
        except Exception as exc:
            session.status = SessionStatus.ERROR
            store.update(session_id)
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_stream_headers(),
    )


@router.post("/sessions/{session_id}/tasks/{task_id}/confirm")
async def confirm_session_task(
    session_id: str,
    task_id: str,
    req: ConfirmSessionTaskRequest,
):
    """在会话流里确认或拒绝一个文档任务"""
    store = get_session_store()
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        user_text = req.user_input
        if not user_text:
            user_text = (
                "确认执行当前文档任务"
                if req.confirmed
                else "拒绝当前文档任务"
            )
        task_message = _run_task_confirmation(
            session,
            task_id,
            req.confirmed,
            user_text=user_text,
            resume_input=req.user_input,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        session.status = SessionStatus.ERROR
        store.update(session_id)
        raise HTTPException(status_code=500, detail=f"任务处理失败: {exc}") from exc

    store.update(session_id)
    return {"message": task_message.model_dump(), "session": _session_detail(session)}


def _load_uploaded_files(file_ids: list[str]) -> tuple[str, list[dict], list]:
    file_context = ""
    file_info: list[dict] = []
    document_records = []
    file_store = get_file_store()

    for file_id in file_ids:
        record = file_store.get_file(file_id)
        if not record:
            continue

        info = {
            "id": record.id,
            "filename": record.original_name,
            "file_type": record.file_type,
            "extension": record.extension,
            "size_bytes": record.size_bytes,
        }
        file_info.append(info)

        if record.extension in DOC_TASK_EXTENSIONS:
            document_records.append(record)

        if record.file_type == "image":
            file_context += f"\n[图片: {record.original_name}]\n"
        elif record.extracted_text:
            file_context += f"\n[文件: {record.original_name}]\n{record.extracted_text}\n"

    return file_context, file_info, document_records


def _maybe_handle_task_message(
    session: Session,
    content: str,
    file_info: list[dict],
    document_records: list,
) -> Message | None:
    if document_records:
        return _create_document_task(session, content, file_info, document_records[0])

    pending_task = _find_pending_task_event(session)
    if pending_task is None:
        return None

    confirmation_request = pending_task.get("confirmation_request") or {}
    kind = confirmation_request.get("kind")

    if kind == ConfirmationKind.AMBIGUITY_RESOLUTION.value:
        return _run_task_confirmation(
            session,
            pending_task["task_id"],
            True,
            user_text=content,
            resume_input=content,
        )

    confirmed = _parse_confirmation_intent(content)
    if confirmed is None:
        return None

    return _run_task_confirmation(
        session,
        pending_task["task_id"],
        confirmed,
        user_text=content,
    )


def _create_document_task(
    session: Session,
    user_input: str,
    file_info: list[dict],
    document_record,
) -> Message:
    response_started_at = perf_counter()
    _append_user_message(session, user_input, file_info)
    response = get_task_service().create_and_plan(
        document_record.file_path,
        user_input,
    )
    task_message = _build_task_message(
        response,
        response_ms=int((perf_counter() - response_started_at) * 1000),
    )
    session.messages.append(task_message)
    _sync_session_status(session, response["status"])
    return task_message


def _run_task_confirmation(
    session: Session,
    task_id: str,
    confirmed: bool,
    user_text: str,
    resume_input: str | None = None,
) -> Message:
    response_started_at = perf_counter()
    _append_user_message(session, user_text, [])
    response = get_task_service().confirm_and_execute(
        task_id,
        confirmed,
        user_input=resume_input,
    )
    task_message = _build_task_message(
        response,
        response_ms=int((perf_counter() - response_started_at) * 1000),
    )
    session.messages.append(task_message)
    _sync_session_status(session, response["status"])
    return task_message


def _append_user_message(
    session: Session,
    content: str,
    file_info: list[dict],
) -> None:
    metadata = {"files": file_info} if file_info else {}
    session.messages.append(
        Message(
            role="user",
            content=content,
            metadata=metadata,
        )
    )


def _find_pending_task_event(session: Session) -> dict | None:
    for message in reversed(session.messages):
        task_event = message.metadata.get("task_event") if message.metadata else None
        if task_event and task_event.get("status") == "awaiting_confirm":
            return task_event
    return None


def _parse_confirmation_intent(content: str) -> bool | None:
    normalized = content.strip().lower().rstrip("。.!！?？")
    if normalized in APPROVE_WORDS:
        return True
    if normalized in REJECT_WORDS:
        return False
    return None


def _build_task_message(task_response: dict, response_ms: int | None = None) -> Message:
    task_event = {
        "task_id": task_response["task_id"],
        "status": task_response["status"],
        "plan_display": task_response.get("plan_display", ""),
        "confirmation_request": task_response.get("confirmation_request"),
        "result": task_response.get("result"),
        "message": task_response.get("message"),
        "error": task_response.get("error"),
    }
    return Message(
        role="assistant",
        content=_build_task_summary(task_event),
        metadata={
            "task_event": task_event,
            **({"response_ms": response_ms} if response_ms is not None else {}),
        },
    )


def _build_task_summary(task_event: dict) -> str:
    confirmation_request = task_event.get("confirmation_request") or {}
    kind = confirmation_request.get("kind")
    status = task_event.get("status")

    if status == "awaiting_confirm" and kind == ConfirmationKind.AMBIGUITY_RESOLUTION.value:
        return "文档任务存在歧义，需要你补充说明后我再继续分析。"
    if status == "awaiting_confirm":
        return "我已经分析了文档并生成执行计划，请确认后继续。"
    if status == "done":
        return "文档任务已执行完成。"
    if status == "rejected":
        return "文档任务已按你的要求停止。"
    if status == "failed":
        return "文档任务执行失败，请查看下方结果。"
    if status == "planned":
        return "文档任务已重新规划。"
    return "文档任务状态已更新。"


def _sync_session_status(session: Session, task_status: str) -> None:
    if task_status == "awaiting_confirm":
        session.status = SessionStatus.AWAITING_CONFIRMATION
    elif task_status == "failed":
        session.status = SessionStatus.ERROR
    else:
        session.status = SessionStatus.IDLE


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


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
