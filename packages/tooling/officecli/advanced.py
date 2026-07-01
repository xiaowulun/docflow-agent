"""
OfficeCLI 高级命令封装

补充 watch/mark/refresh/dump/add-part 等当前项目未直接暴露的命令，
并提供一个受限的 office_command 透传入口，便于覆盖官方 CLI 的完整能力面。
"""
from __future__ import annotations

from typing import Any

from packages.tooling.officecli.wrapper import format_props, run_officecli
from packages.tooling.registry import ToolRegistry


@ToolRegistry.register("office_command")
def office_command(
    args: list[str],
    expect_json: bool = True,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    透传调用 officecli 命令。

    Args:
        args: 传给 officecli 的参数数组，不要包含二进制名本身。
        expect_json: 是否期待 JSON 输出，默认 true。
        timeout: 超时时间（秒）。
    """
    normalized = list(args)
    if normalized and normalized[0] == "officecli":
        normalized = normalized[1:]
    return run_officecli(normalized, expect_json=expect_json, timeout=timeout)


@ToolRegistry.register("office_watch")
def office_watch(file_path: str, port: int | None = None) -> dict[str, Any]:
    """启动 Office 文档实时预览服务。"""
    args = ["watch", file_path]
    if port is not None:
        args.extend(["--port", str(port)])
    return run_officecli(args)


@ToolRegistry.register("office_unwatch")
def office_unwatch(file_path: str) -> dict[str, Any]:
    """停止 Office 文档实时预览服务。"""
    return run_officecli(["unwatch", file_path])


@ToolRegistry.register("office_mark")
def office_mark(
    file_path: str,
    path: str,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """给 watch 预览中的元素添加内存标记。"""
    args = ["watch", file_path, "mark", file_path, path]
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("office_unmark")
def office_unmark(
    file_path: str,
    path: str | None = None,
    remove_all: bool = False,
) -> dict[str, Any]:
    """删除 watch 预览中的元素标记。"""
    args = ["watch", file_path, "unmark", file_path]
    if path:
        args.extend(["--path", path])
    if remove_all:
        args.append("--all")
    return run_officecli(args)


@ToolRegistry.register("office_get_marks")
def office_get_marks(file_path: str) -> dict[str, Any]:
    """列出 watch 预览中的所有标记。"""
    return run_officecli(["watch", file_path, "marks", file_path])


@ToolRegistry.register("office_goto")
def office_goto(file_path: str, path: str) -> dict[str, Any]:
    """让 watch 预览滚动到指定元素。"""
    return run_officecli(["watch", file_path, "goto", file_path, path])


@ToolRegistry.register("office_refresh")
def office_refresh(file_path: str) -> dict[str, Any]:
    """刷新派生字段，如目录页码、交叉引用等。"""
    return run_officecli(["refresh", file_path])


@ToolRegistry.register("dump_docx")
def dump_docx(
    file_path: str,
    path: str = "/",
    format: str = "batch",
    out: str | None = None,
) -> dict[str, Any]:
    """导出 Word 子树为可回放的批处理脚本。"""
    args = ["dump", file_path, path, "--format", format]
    if out is not None:
        args.extend(["--out", out])
    return run_officecli(args)


@ToolRegistry.register("dump_pptx")
def dump_pptx(
    file_path: str,
    path: str = "/",
    format: str = "batch",
    out: str | None = None,
) -> dict[str, Any]:
    """导出 PPT 子树为可回放的批处理脚本。"""
    args = ["dump", file_path, path, "--format", format]
    if out is not None:
        args.extend(["--out", out])
    return run_officecli(args)


def _add_part(file_path: str, parent: str, part_type: str) -> dict[str, Any]:
    return run_officecli(["add-part", file_path, parent, "--type", part_type])


@ToolRegistry.register("add_part_docx")
def add_part_docx(file_path: str, parent: str, part_type: str) -> dict[str, Any]:
    """为 Word 文档创建新部件，返回 relationship ID。"""
    return _add_part(file_path, parent, part_type)


@ToolRegistry.register("add_part_xlsx")
def add_part_xlsx(file_path: str, parent: str, part_type: str) -> dict[str, Any]:
    """为 Excel 工作簿创建新部件，返回 relationship ID。"""
    return _add_part(file_path, parent, part_type)


@ToolRegistry.register("add_part_pptx")
def add_part_pptx(file_path: str, parent: str, part_type: str) -> dict[str, Any]:
    """为 PPT 演示文稿创建新部件，返回 relationship ID。"""
    return _add_part(file_path, parent, part_type)
