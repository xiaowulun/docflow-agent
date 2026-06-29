"""
OfficeCLI 驻留模式工具

通过 open/close/save 保持文档在内存中，避免每次操作都重新打开文件。
适用于需要多次操作的场景，性能提升 10 倍以上。
"""

from typing import Any

from packages.tooling.officecli.wrapper import run_officecli
from packages.tooling.registry import ToolRegistry


@ToolRegistry.register("office_open")
def office_open(file_path: str) -> dict[str, Any]:
    """
    打开文档并保持在内存中（驻留模式）。

    后续操作会更快，因为不需要每次都重新打开文件。
    使用完毕后必须调用 office_close 或 office_save 释放文件。

    Args:
        file_path: Office 文件路径。

    Returns:
        操作结果。
    """
    return run_officecli(["open", file_path])


@ToolRegistry.register("office_close")
def office_close(file_path: str) -> dict[str, Any]:
    """
    关闭驻留的文档，将内存中的更改刷新到磁盘并释放文件。

    Args:
        file_path: Office 文件路径。

    Returns:
        操作结果。
    """
    return run_officecli(["close", file_path])


@ToolRegistry.register("office_save")
def office_save(file_path: str) -> dict[str, Any]:
    """
    将内存中的更改刷新到磁盘，但保持驻留模式继续运行。

    适用于需要在驻留模式下让其他程序读取最新内容的场景。

    Args:
        file_path: Office 文件路径。

    Returns:
        操作结果。
    """
    return run_officecli(["save", file_path])
