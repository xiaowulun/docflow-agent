"""
内置工具集

每个工具定义两部分：
1. OpenAI function calling 格式的 schema（type: function）
2. Python 执行函数

这些工具是确定性的、无副作用的，用来验证 agent 的 tool calling 闭环。
后续挂文件工具（read_docx 等）时，在下面按相同格式追加即可。
"""

from datetime import datetime

# ---------------------------------------------------------------------------
# 工具 1：获取当前时间
# ---------------------------------------------------------------------------

get_current_time_schema = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前的日期和时间。当用户询问现在几点、今天日期时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "可选，时区，默认本地时间",
                }
            },
            "required": [],
        },
    },
}


def get_current_time(timezone: str = "local") -> dict:
    """获取当前时间"""
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timezone": timezone,
    }


# ---------------------------------------------------------------------------
# 工具 2：计算器
# ---------------------------------------------------------------------------

calculator_schema = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "进行四则运算。当用户需要数学计算时使用，不要自己心算。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如 '3 + 5 * 2' 或 '(10 - 3) / 2'",
                }
            },
            "required": ["expression"],
        },
    },
}


def calculator(expression: str) -> dict:
    """安全计算数学表达式

    注意：这里用受限的 eval，只允许数字和运算符。
    真实生产环境应换成 ast 解析，这里为示例简化。
    """
    # 只允许数字、运算符、空格、小括号、小数点
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return {"error": "表达式包含非法字符", "expression": expression}
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": f"计算失败: {e}", "expression": expression}


# ---------------------------------------------------------------------------
# 工具 3：字符串长度
# ---------------------------------------------------------------------------

string_length_schema = {
    "type": "function",
    "function": {
        "name": "string_length",
        "description": "计算字符串的字符数。当用户问某个字符串有多长时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要计算长度的字符串",
                }
            },
            "required": ["text"],
        },
    },
}


def string_length(text: str) -> dict:
    """计算字符串长度"""
    return {"text": text, "length": len(text)}


# ---------------------------------------------------------------------------
# 汇总注册
# ---------------------------------------------------------------------------

# 所有工具的 schema（传给 LLM 的 tools 参数）
BUILTIN_TOOLS = [
    get_current_time_schema,
    calculator_schema,
    string_length_schema,
]

# 工具名 -> 执行函数
BUILTIN_TOOL_FUNCS = {
    "get_current_time": get_current_time,
    "calculator": calculator,
    "string_length": string_length,
}


def get_tool_schemas() -> list[dict]:
    """返回所有工具的 schema（供 LLM 使用）"""
    return BUILTIN_TOOLS


def get_tool_func(name: str):
    """根据工具名获取执行函数"""
    return BUILTIN_TOOL_FUNCS.get(name)
