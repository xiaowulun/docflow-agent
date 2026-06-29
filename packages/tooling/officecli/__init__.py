"""
OfficeCLI 工具封装

将 officecli 二进制包装为 agent 可调用的工具，提供 Word/Excel/PPT 的
创建、读取、修改、分析能力。
"""

from packages.tooling.officecli.wrapper import (
    OfficeCLIError,
    find_binary,
    format_props,
    is_available,
    run_officecli,
)

__all__ = [
    "OfficeCLIError",
    "find_binary",
    "format_props",
    "is_available",
    "run_officecli",
]
