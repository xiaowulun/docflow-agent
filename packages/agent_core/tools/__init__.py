"""
工具包

所有供 agent 调用的工具统一定义在此。
每个工具包含：
- OpenAI function calling 格式的 schema（name/description/parameters）
- 对应的 Python 执行函数

后续挂文件工具（read_docx 等）时，按同样格式加进来即可。
"""

from .builtin import (
    BUILTIN_TOOL_FUNCS,
    BUILTIN_TOOLS,
    get_tool_func,
    get_tool_schemas,
)

__all__ = [
    "BUILTIN_TOOLS",
    "BUILTIN_TOOL_FUNCS",
    "get_tool_func",
    "get_tool_schemas",
]
