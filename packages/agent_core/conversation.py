"""
ConversationAgent - 对话型 Agent

这是 agent 的核心：一个 think → act → observe 的对话循环。
与旧的 planner（只调一次 LLM 生成静态计划）不同，这里：
1. 把用户消息加入历史，调 LLM
2. LLM 如果返回 tool_call → 执行工具，把结果作为 tool 消息喂回历史
3. 再调 LLM，让它基于工具结果生成最终回复
4. 循环直到 LLM 不再调用工具（返回纯文本），即完成

这就是你学的 ReAct 的受控版本：有工具调用闭环，但单轮内收敛（不无限循环）。
"""

import json
from time import perf_counter
from typing import Generator

from openai import OpenAI

from config import settings
from packages.schemas.conversation import (
    Message,
    Session,
    SessionStatus,
    ToolCallInfo,
    ToolInfo,
)
from packages.agent_core.tools import BUILTIN_TOOLS, get_tool_func
from packages.agent_core.tools.builtin import (
    reset_current_session_id,
    set_current_session_id,
)


class ConversationAgent:
    """对话型 Agent

    使用方式：
        agent = ConversationAgent()
        agent.init_session(session)
        reply = agent.chat(session, "现在几点？")
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60,
        )
        self.model = settings.llm_model
        
        # Agnes 视觉模型客户端
        self.agnes_client = None
        if settings.agnes_api_key:
            self.agnes_client = OpenAI(
                api_key=settings.agnes_api_key,
                base_url=settings.agnes_base_url,
                timeout=120,
            )

    def _needs_vision_model(self, messages: list[dict]) -> bool:
        """
        检测是否需要视觉模型。
        
        判断逻辑：
        1. 消息中包含图片（image_url 类型）
        2. 用户明确要求分析图片
        """
        for msg in messages:
            content = msg.get("content", "")
            
            # 检查是否有图片内容
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        return True
            
            # 检查用户消息是否包含图片相关关键词
            if msg.get("role") == "user" and isinstance(content, str):
                vision_keywords = ["图片", "图像", "照片", "截图", "分析一下这张", "看看这个图"]
                if any(kw in content for kw in vision_keywords):
                    return True
        
        return False

    def _get_model_and_client(self, messages: list[dict]):
        """
        根据消息内容选择合适的模型和客户端。
        
        Returns:
            (client, model): 客户端和模型名称
        """
        if self._needs_vision_model(messages) and self.agnes_client:
            return self.agnes_client, settings.agnes_vision_model
        return self.client, self.model

    def get_available_tools(self) -> list[ToolInfo]:
        """返回可用工具的展示信息"""
        return [
            ToolInfo(
                name=t["function"]["name"],
                description=t["function"]["description"],
            )
            for t in BUILTIN_TOOLS
        ]

    def chat(self, session: Session, user_input: str) -> str:
        """
        处理一轮用户输入，返回 assistant 的最终文本回复。

        内部会执行完整的 think → act → observe 循环，
        所有中间步骤（tool_call、tool 结果）都记录到 session.messages。

        Args:
            session: 会话对象（会被修改：追加消息、更新状态）
            user_input: 用户输入文本

        Returns:
            assistant 的最终回复文本
        """
        session.messages.append(Message(role="user", content=user_input))

        if session.title == "新会话" and len(session.messages) == 1:
            session.title = user_input[:20] + ("..." if len(user_input) > 20 else "")

        session.status = SessionStatus.THINKING
        session.touch()

        max_iterations = 5
        final_reply = ""
        changed_content = False
        saved_content = False
        response_started_at = perf_counter()

        for _ in range(max_iterations):
            api_messages = self._build_api_messages(session)

            client, model = self._get_model_and_client(api_messages)
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                tools=BUILTIN_TOOLS,
                temperature=0.7,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            if assistant_msg.tool_calls:
                tool_call_infos = []

                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except Exception:
                        arguments = {}

                    tool_call_infos.append(
                        ToolCallInfo(
                            id=tc.id, name=tool_name, arguments=arguments
                        )
                    )

                session.messages.append(
                    Message(
                        role="assistant",
                        content=assistant_msg.content or "",
                        tool_calls=tool_call_infos,
                    )
                )
                session.status = SessionStatus.CALLING_TOOL
                session.touch()

                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except Exception:
                        arguments = {}

                    tool_func = get_tool_func(tool_name)
                    if tool_func is None:
                        tool_result = {"error": f"未知工具: {tool_name}"}
                    else:
                        if tool_name == "save_content":
                            session.status = SessionStatus.SAVING
                            session.touch()
                        token = set_current_session_id(session.id)
                        try:
                            tool_result = tool_func(**arguments)
                        except Exception as e:
                            tool_result = {"error": f"工具执行失败: {e}"}
                        finally:
                            reset_current_session_id(token)

                    if tool_name in {"write_content", "edit_content"} and "error" not in tool_result:
                        changed_content = True
                    if tool_name == "save_content" and "error" not in tool_result:
                        saved_content = True

                    session.messages.append(
                        Message(
                            role="tool",
                            content=json.dumps(tool_result, ensure_ascii=False),
                            tool_name=tool_name,
                            tool_call_id=tc.id,
                        )
                    )

                session.status = SessionStatus.THINKING
                session.touch()
                continue

            final_reply = assistant_msg.content or ""
            if not final_reply.strip():
                final_reply = self._generate_forced_final_reply(session)
            session.messages.append(
                Message(
                    role="assistant",
                    content=final_reply,
                    metadata={
                        "response_ms": int((perf_counter() - response_started_at) * 1000)
                    },
                )
            )
            break
        else:
            final_reply = self._generate_forced_final_reply(session)
            session.messages.append(
                Message(
                    role="assistant",
                    content=final_reply,
                    metadata={
                        "response_ms": int((perf_counter() - response_started_at) * 1000)
                    },
                )
            )

        if changed_content and not saved_content:
            session.status = SessionStatus.AWAITING_CONFIRMATION
        else:
            session.status = SessionStatus.IDLE
        session.touch()

        return final_reply

    def chat_stream(self, session: Session, user_input: str, file_context: str = "", file_ids: list[str] = None, file_info: list[dict] = None) -> Generator[str, None, None]:
        """
        流式版本：yield 每个文本块，供 SSE 使用。
        工具调用过程通过特殊事件通知前端。
        """
        # 存储用户原始消息（不包含文件内容，但记录文件信息）
        user_msg = Message(role="user", content=user_input)
        if file_info:
            user_msg.metadata = {"files": file_info}
        session.messages.append(user_msg)
        
        # 设置会话标题（使用用户的第一条消息）
        if session.title == "新会话" and len(session.messages) == 1:
            session.title = user_input[:20] + ("..." if len(user_input) > 20 else "")

        session.status = SessionStatus.THINKING
        session.touch()

        max_iterations = 5
        changed_content = False
        saved_content = False
        response_started_at = perf_counter()
        final_content = ""

        for _ in range(max_iterations):
            api_messages = self._build_api_messages(session)
            
            # 如果有文件内容,作为系统上下文追加到第一条用户消息前
            if file_context and _ == 0:
                # 找到第一条用户消息的位置
                for i, msg in enumerate(api_messages):
                    if msg["role"] == "user":
                        api_messages.insert(i, {
                            "role": "system",
                            "content": f"用户上传的文件内容:\n{file_context}"
                        })
                        break

            client, model = self._get_model_and_client(api_messages)
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                tools=BUILTIN_TOOLS,
                temperature=0.7,
                stream=True,
            )

            # 收集流式响应
            content_chunks = []
            tool_calls_data = {}  # id -> {name, arguments}

            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # 处理工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {"id": tc.id, "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments

                # 处理文本内容
                if delta.content:
                    content_chunks.append(delta.content)
                    yield delta.content

            # 如果有工具调用
            if tool_calls_data:
                tool_call_infos = []
                for idx in sorted(tool_calls_data.keys()):
                    data = tool_calls_data[idx]
                    try:
                        arguments = json.loads(data["arguments"])
                    except Exception:
                        arguments = {}
                    tool_call_infos.append(
                        ToolCallInfo(
                            id=data["id"],
                            name=data["name"],
                            arguments=arguments,
                        )
                    )

                session.messages.append(
                    Message(
                        role="assistant",
                        content="".join(content_chunks) if content_chunks else "",
                        tool_calls=tool_call_infos,
                    )
                )

                # 通知前端工具调用开始
                yield f"\0TOOL_CALL_START:{json.dumps([tc.name for tc in tool_call_infos])}\0"

                session.status = SessionStatus.CALLING_TOOL
                session.touch()

                # 执行工具
                for tc_info in tool_call_infos:
                    tool_func = get_tool_func(tc_info.name)
                    if tool_func is None:
                        tool_result = {"error": f"未知工具: {tc_info.name}"}
                    else:
                        if tc_info.name == "save_content":
                            session.status = SessionStatus.SAVING
                            session.touch()
                        token = set_current_session_id(session.id)
                        try:
                            tool_result = tool_func(**tc_info.arguments)
                        except Exception as e:
                            tool_result = {"error": f"工具执行失败: {e}"}
                        finally:
                            reset_current_session_id(token)

                    if tc_info.name in {"write_content", "edit_content"} and "error" not in tool_result:
                        changed_content = True
                    if tc_info.name == "save_content" and "error" not in tool_result:
                        saved_content = True

                    session.messages.append(
                        Message(
                            role="tool",
                            content=json.dumps(tool_result, ensure_ascii=False),
                            tool_name=tc_info.name,
                            tool_call_id=tc_info.id,
                        )
                    )

                    # 通知前端工具结果
                    yield f"\0TOOL_RESULT:{tc_info.name}:{json.dumps(tool_result, ensure_ascii=False)}\0"

                session.status = SessionStatus.THINKING
                session.touch()
                continue

            # 没有工具调用，完成
            final_content = "".join(content_chunks)
            if not final_content.strip():
                final_content = self._generate_forced_final_reply(session)
                yield final_content
            session.messages.append(
                Message(
                    role="assistant",
                    content=final_content,
                    metadata={
                        "response_ms": int((perf_counter() - response_started_at) * 1000)
                    },
                )
            )
            break
        else:
            final_content = ""
            for chunk in self._stream_forced_final_reply(session):
                final_content += chunk
                yield chunk
            session.messages.append(
                Message(
                    role="assistant",
                    content=final_content,
                    metadata={
                        "response_ms": int((perf_counter() - response_started_at) * 1000)
                    },
                )
            )

        if changed_content and not saved_content:
            session.status = SessionStatus.AWAITING_CONFIRMATION
        else:
            session.status = SessionStatus.IDLE
        session.touch()

        # 结束标记
        yield "\0DONE\0"

    def _generate_forced_final_reply(self, session: Session) -> str:
        """工具链结束后强制生成一条面向用户的最终回复。"""
        api_messages = self._build_api_messages(session)
        api_messages.append(
            {
                "role": "system",
                "content": (
                    "你已经拿到了足够的工具结果。"
                    "现在不要再调用任何工具，直接基于现有上下文给用户一条完整、自然的最终回答。"
                ),
            }
        )
        client, model = self._get_model_and_client(api_messages)
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=0.7,
        )
        return response.choices[0].message.content or "我已经处理完成，但暂时没有生成可展示的最终说明。"

    def _stream_forced_final_reply(self, session: Session) -> Generator[str, None, None]:
        """流式兜底最终回复，避免工具调用上限后页面没有 assistant 文本。"""
        api_messages = self._build_api_messages(session)
        api_messages.append(
            {
                "role": "system",
                "content": (
                    "你已经拿到了足够的工具结果。"
                    "现在不要再调用任何工具，直接基于现有上下文给用户一条完整、自然的最终回答。"
                ),
            }
        )
        client, model = self._get_model_and_client(api_messages)
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=0.7,
            stream=True,
        )
        yielded = False
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yielded = True
                yield delta.content

        if not yielded:
            yield "我已经处理完成，但暂时没有生成可展示的最终说明。"

    def _build_api_messages(self, session: Session) -> list[dict]:
        """
        把 session.messages 转换成 OpenAI API 需要的格式。

        关键：assistant 的 tool_calls 和 tool 消息的 tool_call_id
        要用 OpenAI 原生格式，否则 API 会报错。
        """
        api_messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "你是一个极简的 pi agent。"
                    "你能聊天、维护上下文，并通过工具管理当前会话内的内容草稿。"
                    "当用户提问涉及实时资讯、新闻、价格、天气、或其他需要联网才能回答的问题时，使用 web_search 工具搜索最新信息。"
                    "当用户要写新内容时，先生成完整正文，再调用 write_content 写入草稿。"
                    "当用户要查看已有内容时，优先使用 list_contents 或 read_content。"
                    "当用户要修改、润色、扩写或重写已有内容时，先读取原文，再生成更新后的完整正文，并调用 edit_content。"
                    "写完或改完后，不要自动保存文件。你必须先把正文展示给用户，然后另起一段询问是否需要保存，并说明默认保存为 md。"
                    "只有用户明确同意保存时，才能调用 save_content；如果用户没有指定格式，默认使用 md。"
                    "回复时必须使用纯自然中文，绝对禁止使用任何 Markdown 格式：不要用星号加粗、不要用井号标题、不要用竖线表格、不要用反引号代码块、不要用短横线或数字做列表符号。"
                    "直接用自然的口语化中文回答，段落之间空行即可，列举内容时直接用文字叙述或用数字加顿号（如：1、2、3、）。"
                    "除非用户明确要求列出内部细节，否则不要提及工具名称或技术实现。"
                    "\n\n"
                    "【OfficeCLI 使用规范 - 重要】"
                    "处理 Word、Excel、PPT 时，优先使用 officecli 官方能力，不要默认退化成空白文档加零碎拼装。"
                    "当不确定属性名、命令语法、元素类型、参数格式或官方能力边界时，必须先调用 office_help，不要猜。"
                    "当用户提供了现成模板或明确说按模板生成时，优先考虑 merge_document。"
                    "当一个 Office 任务需要多步编辑时，优先考虑 batch_docx、batch_xlsx、batch_pptx。"
                    "当需要浏览器预览、定位、人工复核、给元素打标记时，可以使用 office_watch、office_goto、office_mark、office_get_marks。"
                    "当需要导出回放脚本或创建高级部件时，可以使用 dump_docx、dump_pptx、add_part_docx、add_part_xlsx、add_part_pptx。"
                    "如果现有独立工具仍覆盖不了官方命令面，可以使用 office_command 直接调用 officecli 子命令。"
                    "完成重要 Office 文档生成或修改后，优先用 validate_docx、validate_xlsx、validate_pptx 或 view_* 的 issues、html、screenshot 模式做自检。"
                    "\n\n"
                    "【PPT 制作规范】"
                    "创建 PPT 时，默认优先使用 add_pptx_slide_with_layout。"
                    "只有在需要精细控制位置、原生批量命令或官方高级能力时，才改用 add_pptx、batch_pptx 或 office_command。"
                ),
            }
        ]

        for m in session.messages:
            if m.role == "user":
                api_messages.append({"role": "user", "content": m.content})

            elif m.role == "assistant":
                if m.tool_calls:
                    api_messages.append(
                        {
                            "role": "assistant",
                            "content": m.content or None,
                            "tool_calls": [
                                {
                                    "id": tc.id or f"call_{i}",
                                    "type": "function",
                                    "function": {
                                        "name": tc.name,
                                        "arguments": _json_dumps(tc.arguments),
                                    },
                                }
                                for i, tc in enumerate(m.tool_calls)
                            ],
                        }
                    )
                else:
                    api_messages.append(
                        {"role": "assistant", "content": m.content}
                    )

            elif m.role == "tool":
                api_messages.append(
                    {
                        "role": "tool",
                        "content": m.content,
                        "tool_call_id": m.tool_call_id or "",
                    }
                )

        return api_messages


def _json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)
