"""
Word (.docx) 工具封装

基于 officecli 提供 Word 文档的 L1-L2 层操作。
"""
from __future__ import annotations

from typing import Any

from packages.tooling.officecli.wrapper import format_props, run_officecli
from packages.tooling.registry import ToolRegistry


@ToolRegistry.register("create_docx")
def create_docx(path: str) -> dict[str, Any]:
    """
    创建一个空白 Word 文档。

    Args:
        path: 目标文件路径，必须以 .docx 结尾。

    Returns:
        officecli 返回的结构化结果。
    """
    return run_officecli(["create", path])


@ToolRegistry.register("view_docx")
def view_docx(file_path: str, mode: str = "outline") -> dict[str, Any]:
    """
    查看 Word 文档的语义化视图。

    Args:
        file_path: Word 文件路径。
        mode: 视图模式，可选 outline | stats | issues | text | annotated | html。

    Returns:
        结构化视图结果。
    """
    return run_officecli(["view", file_path, mode])


@ToolRegistry.register("get_docx")
def get_docx(file_path: str, path: str, depth: int | None = None) -> dict[str, Any]:
    """
    获取 Word 文档中指定路径的元素 JSON。

    Args:
        file_path: Word 文件路径。
        path: 元素路径，例如 /body/p[1]、/body/tbl[1]。
        depth: 展开子元素的深度，可选。

    Returns:
        元素结构化数据。
    """
    args = ["get", file_path, path]
    if depth is not None:
        args.extend(["--depth", str(depth)])
    return run_officecli(args)


@ToolRegistry.register("query_docx")
def query_docx(file_path: str, selector: str) -> dict[str, Any]:
    """
    使用 CSS-like 选择器查询 Word 文档元素。

    Args:
        file_path: Word 文件路径。
        selector: CSS-like 选择器，例如 "paragraph[style=Heading1]"、"run:contains(TODO)"。

    Returns:
        匹配元素列表。
    """
    return run_officecli(["query", file_path, selector])


@ToolRegistry.register("set_docx")
def set_docx(
    file_path: str,
    path: str,
    props: dict[str, Any] | None = None,
    find: str | None = None,
    replace: str | None = None,
) -> dict[str, Any]:
    """
    修改 Word 文档中指定路径的元素属性或文本。

    Args:
        file_path: Word 文件路径。
        path: 元素路径，例如 /body/p[1]、/body/p[1]/r[1]。
        props: 属性字典，例如 {"text": "新标题", "style": "Heading1", "bold": "true"}。
        find: 可选，要查找的文本片段。
        replace: 可选，要替换成的文本。

    Returns:
        操作结果。
    """
    args = ["set", file_path, path]
    args.extend(format_props(props))
    if find is not None:
        args.extend(["--find", find])
    if replace is not None:
        args.extend(["--replace", replace])
    return run_officecli(args)


@ToolRegistry.register("add_docx")
def add_docx(
    file_path: str,
    parent: str,
    element_type: str,
    props: dict[str, Any] | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """
    在 Word 文档指定父节点下添加新元素。

    Args:
        file_path: Word 文件路径。
        parent: 父节点路径，例如 /body。
        element_type: 元素类型，例如 paragraph、run、table、image 等。
        props: 元素属性字典。
        after: 可选，插入到该路径之后。
        before: 可选，插入到该路径之前。

    Returns:
        操作结果。
    """
    args = ["add", file_path, parent, "--type", element_type]
    if after is not None:
        args.extend(["--after", after])
    if before is not None:
        args.extend(["--before", before])
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("remove_docx")
def remove_docx(file_path: str, path: str) -> dict[str, Any]:
    """
    删除 Word 文档中指定路径的元素。

    Args:
        file_path: Word 文件路径。
        path: 要删除的元素路径。

    Returns:
        操作结果。
    """
    return run_officecli(["remove", file_path, path])


@ToolRegistry.register("move_docx")
def move_docx(
    file_path: str,
    path: str,
    to: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """
    移动 Word 文档中的元素到新位置。

    Args:
        file_path: Word 文件路径。
        path: 要移动的元素路径。
        to: 目标父节点路径。
        after: 插入到该路径之后。
        before: 插入到该路径之前。

    Returns:
        操作结果。
    """
    args = ["move", file_path, path]
    if to is not None:
        args.extend(["--to", to])
    if after is not None:
        args.extend(["--after", after])
    if before is not None:
        args.extend(["--before", before])
    return run_officecli(args)


@ToolRegistry.register("swap_docx")
def swap_docx(file_path: str, path1: str, path2: str) -> dict[str, Any]:
    """
    交换 Word 文档中两个元素的位置。

    Args:
        file_path: Word 文件路径。
        path1: 第一个元素路径。
        path2: 第二个元素路径。

    Returns:
        操作结果。
    """
    return run_officecli(["swap", file_path, path1, path2])


@ToolRegistry.register("raw_docx")
def raw_docx(file_path: str, part: str = "/document") -> dict[str, Any]:
    """
    查看 Word 文档的原始 XML（兜底方案）。

    Args:
        file_path: Word 文件路径。
        part: 文档部件路径，例如 /document、/styles、/numbering。

    Returns:
        XML 内容。
    """
    return run_officecli(["raw", file_path, part], expect_json=False)


@ToolRegistry.register("raw_set_docx")
def raw_set_docx(
    file_path: str,
    part: str,
    xpath: str,
    action: str,
    xml: str | None = None,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    直接修改 Word 文档的原始 XML（兜底方案）。

    Args:
        file_path: Word 文件路径。
        part: 文档部件路径，例如 /document。
        xpath: XPath 表达式定位要修改的元素。
        action: 操作类型，可选 set-attr | add-child | remove。
        xml: 要插入的 XML 片段（add-child 时使用）。
        props: 属性字典（set-attr 时使用）。

    Returns:
        操作结果。
    """
    args = ["raw-set", file_path, part, xpath, action]
    if xml is not None:
        args.extend(["--xml", xml])
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("validate_docx")
def validate_docx(file_path: str) -> dict[str, Any]:
    """
    验证 Word 文档是否符合 OpenXML 规范。

    Args:
        file_path: Word 文件路径。

    Returns:
        验证结果，包含错误和警告列表。
    """
    return run_officecli(["validate", file_path])


@ToolRegistry.register("batch_docx")
def batch_docx(file_path: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    """
    批量执行多个 Word 文档操作（性能优化）。

    Args:
        file_path: Word 文件路径。
        commands: 命令列表，每个命令是一个字典，包含 command 字段和其他参数。
                  例如：[{"command": "add", "parent": "/body", "type": "paragraph", "props": {"text": "Hello"}}]

    Returns:
        批量操作结果。
    """
    import json

    commands_json = json.dumps(commands)
    return run_officecli(["batch", file_path, "--commands", commands_json])


@ToolRegistry.register("clear_docx")
def clear_docx(file_path: str) -> dict[str, Any]:
    """
    清空 Word 文档的所有内容（保留文档结构）。

    删除 body 下的所有段落、表格等元素，但保留文档的样式、页眉页脚等。
    适用于需要完全重写文档内容的场景。

    Args:
        file_path: Word 文件路径。

    Returns:
        操作结果。
    """
    import json

    # 查询所有段落并删除
    result = run_officecli(["query", file_path, "paragraph"])
    if not result.get("success") or not result.get("data"):
        return {"success": True, "message": "文档已为空"}

    # 从 results 字段提取路径
    data = result["data"]
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        paths = [item.get("path") for item in results if isinstance(item, dict) and item.get("path")]
    else:
        paths = []

    if not paths:
        return {"success": True, "message": "文档已为空"}

    commands = [{"command": "remove", "path": path} for path in paths]
    return run_officecli(["batch", file_path, "--commands", json.dumps(commands)])


@ToolRegistry.register("replace_docx")
def replace_docx(file_path: str, new_content: list[dict[str, Any]]) -> dict[str, Any]:
    """
    用新内容完全替换 Word 文档的所有内容。

    先清空文档,然后批量添加新内容。适用于需要完全重写文档的场景。

    Args:
        file_path: Word 文件路径。
        new_content: 新内容列表,每个元素是一个字典,包含 type 和 props。
                     例如：[{"type": "paragraph", "props": {"text": "新标题", "style": "Heading1"}}]

    Returns:
        操作结果。
    """
    import json

    # 先清空
    clear_result = clear_docx(file_path)
    if not clear_result.get("success"):
        return clear_result

    # 再批量添加新内容
    commands = [
        {
            "command": "add",
            "parent": "/body",
            "type": item["type"],
            "props": item.get("props", {}),
        }
        for item in new_content
    ]

    if commands:
        return run_officecli(["batch", file_path, "--commands", json.dumps(commands)])
    return {"success": True, "message": "文档已清空"}
