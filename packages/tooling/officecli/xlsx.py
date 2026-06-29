"""
Excel (.xlsx) 工具封装

基于 officecli 提供 Excel 工作簿的 L1-L2 层操作。
"""
from __future__ import annotations

from typing import Any

from packages.tooling.officecli.wrapper import format_props, run_officecli
from packages.tooling.registry import ToolRegistry


@ToolRegistry.register("create_xlsx")
def create_xlsx(path: str) -> dict[str, Any]:
    """创建一个空白 Excel 工作簿。"""
    return run_officecli(["create", path])


@ToolRegistry.register("view_xlsx")
def view_xlsx(file_path: str, mode: str = "text") -> dict[str, Any]:
    """
    查看 Excel 工作簿的语义化视图。

    Args:
        file_path: Excel 文件路径。
        mode: 视图模式，可选 text | outline | stats | issues | html。
    """
    return run_officecli(["view", file_path, mode])


@ToolRegistry.register("get_xlsx")
def get_xlsx(file_path: str, path: str, depth: int | None = None) -> dict[str, Any]:
    """
    获取 Excel 工作簿中指定路径的元素 JSON。

    Args:
        file_path: Excel 文件路径。
        path: 元素路径，例如 /Sheet1、/Sheet1/A1、/Sheet1/A1:B10。
        depth: 展开子元素的深度。
    """
    args = ["get", file_path, path]
    if depth is not None:
        args.extend(["--depth", str(depth)])
    return run_officecli(args)


@ToolRegistry.register("query_xlsx")
def query_xlsx(file_path: str, selector: str) -> dict[str, Any]:
    """
    使用 CSS-like 选择器查询 Excel 元素。

    Args:
        file_path: Excel 文件路径。
        selector: 选择器，例如 "cell[value>5000]"、"Sheet1!row[Salary>5000]"。
    """
    return run_officecli(["query", file_path, selector])


@ToolRegistry.register("set_xlsx")
def set_xlsx(
    file_path: str,
    path: str,
    props: dict[str, Any] | None = None,
    find: str | None = None,
    replace: str | None = None,
) -> dict[str, Any]:
    """
    修改 Excel 中指定路径的单元格或元素。

    Args:
        file_path: Excel 文件路径。
        path: 元素路径，例如 /Sheet1/A1。
        props: 属性字典，例如 {"value": "100", "bold": "true", "formula": "=SUM(A1:A2)"}。
        find: 可选，查找文本。
        replace: 可选，替换文本。
    """
    args = ["set", file_path, path]
    args.extend(format_props(props))
    if find is not None:
        args.extend(["--find", find])
    if replace is not None:
        args.extend(["--replace", replace])
    return run_officecli(args)


@ToolRegistry.register("add_xlsx")
def add_xlsx(
    file_path: str,
    parent: str,
    element_type: str,
    props: dict[str, Any] | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """
    在 Excel 工作簿中添加新元素。

    Args:
        file_path: Excel 文件路径。
        parent: 父节点路径，例如 /、/Sheet1。
        element_type: 元素类型，例如 sheet、row、col、cell、chart、table、pivottable。
        props: 元素属性字典。
        after/before: 插入位置锚点。
    """
    args = ["add", file_path, parent, "--type", element_type]
    if after is not None:
        args.extend(["--after", after])
    if before is not None:
        args.extend(["--before", before])
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("remove_xlsx")
def remove_xlsx(file_path: str, path: str) -> dict[str, Any]:
    """删除 Excel 中指定路径的元素。"""
    return run_officecli(["remove", file_path, path])


@ToolRegistry.register("move_xlsx")
def move_xlsx(
    file_path: str,
    path: str,
    to: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """移动 Excel 中的元素到新位置。"""
    args = ["move", file_path, path]
    if to is not None:
        args.extend(["--to", to])
    if after is not None:
        args.extend(["--after", after])
    if before is not None:
        args.extend(["--before", before])
    return run_officecli(args)


@ToolRegistry.register("swap_xlsx")
def swap_xlsx(file_path: str, path1: str, path2: str) -> dict[str, Any]:
    """交换 Excel 中两个元素的位置。"""
    return run_officecli(["swap", file_path, path1, path2])


@ToolRegistry.register("raw_xlsx")
def raw_xlsx(file_path: str, part: str = "/xl/workbook") -> dict[str, Any]:
    """查看 Excel 的原始 XML（兜底方案）。"""
    return run_officecli(["raw", file_path, part], expect_json=False)


@ToolRegistry.register("raw_set_xlsx")
def raw_set_xlsx(
    file_path: str,
    part: str,
    xpath: str,
    action: str,
    xml: str | None = None,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """直接修改 Excel 的原始 XML（兜底方案）。"""
    args = ["raw-set", file_path, part, xpath, action]
    if xml is not None:
        args.extend(["--xml", xml])
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("validate_xlsx")
def validate_xlsx(file_path: str) -> dict[str, Any]:
    """验证 Excel 是否符合 OpenXML 规范。"""
    return run_officecli(["validate", file_path])


@ToolRegistry.register("batch_xlsx")
def batch_xlsx(file_path: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    """批量执行多个 Excel 操作（性能优化）。"""
    import json

    commands_json = json.dumps(commands)
    return run_officecli(["batch", file_path, "--commands", commands_json])


@ToolRegistry.register("import_xlsx")
def import_xlsx(
    file_path: str,
    parent_path: str,
    source_file: str,
    format: str = "csv",
) -> dict[str, Any]:
    """
    导入 CSV/TSV 数据到 Excel 工作表。

    Args:
        file_path: Excel 文件路径。
        parent_path: 目标工作表路径，例如 /Sheet1。
        source_file: 源数据文件路径（CSV 或 TSV）。
        format: 数据格式，可选 csv | tsv。

    Returns:
        操作结果。
    """
    return run_officecli(["import", file_path, parent_path, source_file, format])


@ToolRegistry.register("clear_xlsx")
def clear_xlsx(file_path: str) -> dict[str, Any]:
    """
    清空 Excel 工作簿的所有工作表内容。

    删除多余工作表，保留最后一个并清空其内容。适用于需要完全重写内容的场景。

    Args:
        file_path: Excel 文件路径。

    Returns:
        操作结果。
    """
    import json

    # 查询所有工作表
    result = run_officecli(["query", file_path, "sheet"])
    if not result.get("success") or not result.get("data"):
        return {"success": True, "message": "工作簿已为空"}

    # 从 results 字段提取路径
    data = result["data"]
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        paths = [item.get("path") for item in results if isinstance(item, dict) and item.get("path")]
    else:
        paths = []

    if not paths:
        return {"success": True, "message": "工作簿已为空"}

    commands: list[dict[str, Any]] = []

    # 删除多余工作表（保留最后一个）
    for path in paths[:-1]:
        commands.append({"command": "remove", "path": path})

    # 清空最后一个工作表的所有行
    last_sheet = paths[-1]
    row_result = run_officecli(["query", file_path, f"{last_sheet}!row"])
    if row_result.get("success") and row_result.get("data"):
        row_data = row_result["data"]
        if isinstance(row_data, dict) and "results" in row_data:
            for item in row_data["results"]:
                if isinstance(item, dict) and item.get("path"):
                    commands.append({"command": "remove", "path": item["path"]})

    if not commands:
        return {"success": True, "message": "工作簿已清空"}

    return run_officecli(["batch", file_path, "--commands", json.dumps(commands)])


@ToolRegistry.register("replace_xlsx")
def replace_xlsx(file_path: str, new_content: list[dict[str, Any]]) -> dict[str, Any]:
    """
    用新内容完全替换 Excel 工作簿的所有内容。

    先清空工作簿，然后批量添加新内容。适用于需要完全重写内容的场景。

    Args:
        file_path: Excel 文件路径。
        new_content: 新内容列表，每个元素是一个字典，包含 type 和 props。
                     例如：[{"type": "sheet", "props": {"name": "Sheet1"}}]

    Returns:
        操作结果。
    """
    import json

    # 先清空
    clear_result = clear_xlsx(file_path)
    if not clear_result.get("success"):
        return clear_result

    # 再批量添加新内容
    commands = [
        {
            "command": "add",
            "parent": "/",
            "type": item["type"],
            "props": item.get("props", {}),
        }
        for item in new_content
    ]

    if commands:
        return run_officecli(["batch", file_path, "--commands", json.dumps(commands)])
    return {"success": True, "message": "工作簿已清空"}
