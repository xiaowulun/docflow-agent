"""
Planner - 计划生成器

基于分析结果和用户指令，调用 LLM 生成结构化执行计划。
输出 ExecutionPlan，包含要执行的操作列表。
"""

import json

from openai import OpenAI

from config import settings
from packages.schemas.file import FileAnalysis
from packages.schemas.plan import Action, ActionType, ExecutionPlan
from packages.schemas.task import TaskType

# LLM 客户端
client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

SYSTEM_PROMPT = """你是一个文档处理助手。根据用户的指令和文件分析结果，生成结构化的执行计划。

输出 JSON 格式：
{
    "intent": "用户意图的简要描述",
    "actions": [
        {
            "tool_name": "工具名",
            "action_type": "read/write/export",
            "description": "操作描述",
            "params": {},
            "requires_confirmation": true
        }
    ],
    "uncertainties": ["不确定的地方"],
    "expected_output": "预期输出描述"
}

可用工具：
- read_docx: 读取 Word 文档
- extract_docx_structure: 提取 Word 结构
- insert_text_by_anchor: 按锚点插入文本
- fill_template_fields: 填充模板字段
- read_xlsx: 读取 Excel
- write_xlsx_cells: 写入 Excel 单元格
- append_rows: 追加 Excel 行
- read_pdf_text: 读取 PDF 文本
- classify_pdf_type: 判断 PDF 类型
- export_result_file: 导出结果文件

规则：
1. 只读操作的 requires_confirmation 设为 false
2. 写入/导出操作的 requires_confirmation 必须设为 true
3. 如果有不确定的地方，列入 uncertainties
4. params 中的字段名要和工具参数对应
"""


def _parse_json_content(content: str) -> dict:
    """
    容错解析 LLM 返回的 JSON。
    处理以下情况：
    - 纯 JSON
    - 带 ```json ... ``` 包裹
    - 带 ``` ... ``` 包裹
    - 前后有多余空白/换行
    """
    if not content or not content.strip():
        raise ValueError("LLM 返回内容为空")

    text = content.strip()

    # 去掉 markdown 代码块包裹
    if text.startswith("```"):
        # 去掉首行（```json 或 ```）
        lines = text.split("\n")
        lines = lines[1:]  # 去掉首行
        # 去掉末尾的 ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 兜底：尝试提取第一个 { ... } 块
        import re

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"无法解析为 JSON，原始内容:\n{content}")


def generate_plan(
    task_type: TaskType,
    analysis: FileAnalysis,
    user_input: str,
) -> ExecutionPlan:
    """
    生成执行计划。

    Args:
        task_type: 任务类型
        analysis: 文件分析结果
        user_input: 用户指令

    Returns:
        ExecutionPlan 执行计划
    """
    # 构造 prompt
    prompt = f"""用户指令：{user_input}

文件类型：{task_type.value}
文件名：{analysis.file_info.filename}

文件内容摘要：
{analysis.text_content[:2000] if analysis.text_content else "（无文本内容）"}

文档结构：
{json.dumps(analysis.structure, ensure_ascii=False, indent=2) if analysis.structure else "（无结构信息）"}

发现的锚点/字段：
{analysis.anchors or analysis.fields_found or "（无）"}

请生成执行计划。"""

    # 调用 LLM
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    # 解析响应
    content = response.choices[0].message.content
    print(f"[planner] LLM 原始返回:\n{content}")
    plan_data = _parse_json_content(content)

    # 构造 Action 列表
    actions = []
    for action_data in plan_data.get("actions", []):
        action = Action(
            tool_name=action_data["tool_name"],
            action_type=ActionType(action_data["action_type"]),
            description=action_data["description"],
            params=action_data.get("params", {}),
            requires_confirmation=action_data.get("requires_confirmation", True),
        )
        actions.append(action)

    return ExecutionPlan(
        task_id=analysis.file_info.file_id,
        intent=plan_data.get("intent", ""),
        actions=actions,
        uncertainties=plan_data.get("uncertainties", []),
        expected_output=plan_data.get("expected_output", ""),
    )
