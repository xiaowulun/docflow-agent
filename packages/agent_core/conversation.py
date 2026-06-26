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
        agent.init_session(session)  # 注入可用工具信息
        reply = agent.chat(session, "现在几点？")
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60,
        )
        self.model = settings.llm_model

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
        # 1. 用户消息入历史
        session.messages.append(Message(role="user", content=user_input))

        # 2. 进入思考状态
        session.status = SessionStatus.THINKING
        session.touch()

        # 3. 循环：调 LLM -> 可能调工具 -> 再调 LLM
        #    最多循环 5 次，防止工具调用死循环
        max_iterations = 5
        final_reply = ""

        for _ in range(max_iterations):
            # 构造 OpenAI 格式的 messages
            api_messages = self._build_api_messages(session)

            # 调用 LLM（带 tools）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                tools=BUILTIN_TOOLS,
                temperature=0.7,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            # ---- 情况 A：LLM 要调用工具 ----
            if assistant_msg.tool_calls:
                # 记录 assistant 的工具调用意图
                tool_call_infos = []

                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    import json as _json

                    try:
                        arguments = _json.loads(tc.function.arguments)
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

                # 执行每个工具调用
                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    import json as _json

                    try:
                        arguments = _json.loads(tc.function.arguments)
                    except Exception:
                        arguments = {}

                    tool_func = get_tool_func(tool_name)
                    if tool_func is None:
                        tool_result = {"error": f"未知工具: {tool_name}"}
                    else:
                        token = set_current_session_id(session.id)
                        try:
                            tool_result = tool_func(**arguments)
                        except Exception as e:
                            tool_result = {"error": f"工具执行失败: {e}"}
                        finally:
                            reset_current_session_id(token)

                    # 工具结果作为 tool 消息入历史
                    session.messages.append(
                        Message(
                            role="tool",
                            content=_json.dumps(tool_result, ensure_ascii=False),
                            tool_name=tool_name,
                            tool_call_id=tc.id,
                        )
                    )

                session.status = SessionStatus.THINKING
                session.touch()
                # 继续循环，让 LLM 基于工具结果生成回复
                continue

            # ---- 情况 B：LLM 直接给出文本回复（循环结束）----
            final_reply = assistant_msg.content or ""
            session.messages.append(
                Message(role="assistant", content=final_reply)
            )
            break

        # 4. 完成
        session.status = SessionStatus.IDLE
        session.touch()

        return final_reply

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
                    "你能聊天、维护上下文，并通过工具管理当前会话内的内容对象。"
                    "当用户要写新内容时，先产出完整正文，再调用 create_document 保存。"
                    "当用户要查看已有内容时，优先使用 list_documents 或 read_document。"
                    "当用户要修改、润色、扩写或重写已有内容时，先读取原文，再生成更新后的完整正文，并调用 update_document。"
                    "除非用户明确要求列出内部细节，否则用自然中文直接回答。"
                ),
            }
        ]

        for m in session.messages:
            if m.role == "user":
                api_messages.append({"role": "user", "content": m.content})

            elif m.role == "assistant":
                if m.tool_calls:
                    # 带 tool_calls 的 assistant 消息要保留调用结构
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
