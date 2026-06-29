"""
PowerPoint (.pptx) 工具封装

基于 officecli 提供 PPT 演示文稿的 L1-L2 层操作。
"""
from __future__ import annotations

from typing import Any

from packages.tooling.officecli.wrapper import format_props, run_officecli
from packages.tooling.registry import ToolRegistry


@ToolRegistry.register("create_pptx")
def create_pptx(path: str) -> dict[str, Any]:
    """创建一个空白 PowerPoint 演示文稿。"""
    return run_officecli(["create", path])


@ToolRegistry.register("add_pptx_slide_with_layout")
def add_pptx_slide_with_layout(
    file_path: str,
    title: str,
    content: list[dict[str, Any]] | None = None,
    layout: str = "title_content",
) -> dict[str, Any]:
    """
    智能添加幻灯片，自动计算布局位置。

    Args:
        file_path: PPT 文件路径。
        title: 幻灯片标题。
        content: 内容列表，每项包含 type 和 props。
        layout: 布局类型：title_only | title_content | two_column | image_text。

    Returns:
        操作结果。
    """
    # 标准幻灯片尺寸（16:9）
    SLIDE_WIDTH = 33.87  # cm
    SLIDE_HEIGHT = 19.05  # cm
    MARGIN = 1.5  # cm

    # 先查询现有幻灯片数量
    existing_slides = run_officecli(["query", file_path, "slide"])
    current_count = 0
    if existing_slides.get("success") and existing_slides.get("data"):
        data = existing_slides["data"]
        if isinstance(data, list):
            current_count = len(data)
    slide_num = current_count + 1

    # 第一步：添加空白幻灯片（不设置 title/text，避免默认位置问题）
    add_slide_result = run_officecli(["add", file_path, "/", "--type", "slide"])
    if not add_slide_result.get("success"):
        return add_slide_result

    # 第二步：手动添加标题 shape，明确设置位置
    title_props = {
        "text": title,
        "x": f"{MARGIN}cm",
        "y": "1.5cm",
        "width": f"{SLIDE_WIDTH - 2 * MARGIN}cm",
        "height": "2cm",
        "size": "32",
        "bold": "true",
    }
    run_officecli([
        "add", file_path, f"/slide[{slide_num}]",
        "--type", "shape"
    ] + format_props(title_props))

    # 第三步：根据布局类型添加内容（所有内容都作为独立 shape，明确指定位置）
    if not content:
        return {"success": True, "slide_number": slide_num, "message": f"已添加第 {slide_num} 张幻灯片"}

    y_start = 4.5  # cm
    
    if layout == "title_content":
        for i, item in enumerate(content):
            item_props = item.get("props", {}).copy()
            # 强制设置位置，不使用 setdefault
            item_props["x"] = f"{MARGIN}cm"
            item_props["y"] = f"{y_start + i * 2.5}cm"
            item_props["width"] = f"{SLIDE_WIDTH - 2 * MARGIN}cm"
            item_props["height"] = "2cm"
            
            run_officecli([
                "add", file_path, f"/slide[{slide_num}]",
                "--type", item.get("type", "shape")
            ] + format_props(item_props))
    
    elif layout == "two_column":
        col_width = (SLIDE_WIDTH - 3 * MARGIN) / 2
        for i, item in enumerate(content[:2]):
            col_x = MARGIN + i * (col_width + MARGIN)
            item_props = item.get("props", {}).copy()
            item_props.setdefault("x", f"{col_x}cm")
            item_props.setdefault("y", "4.5cm")
            item_props.setdefault("width", f"{col_width}cm")
            item_props.setdefault("height", "12cm")
            
            run_officecli([
                "add", file_path, f"/slide[{slide_num}]",
                "--type", item.get("type", "shape")
            ] + format_props(item_props))
    
    elif layout == "image_text" and len(content) >= 2:
        # 左侧图片
        img_props = content[0].get("props", {}).copy()
        img_props.setdefault("x", f"{MARGIN}cm")
        img_props.setdefault("y", "4.5cm")
        img_props.setdefault("width", "15cm")
        img_props.setdefault("height", "12cm")
        run_officecli([
            "add", file_path, f"/slide[{slide_num}]",
            "--type", content[0].get("type", "picture")
        ] + format_props(img_props))
        
        # 右侧文本
        text_props = content[1].get("props", {}).copy()
        text_props.setdefault("x", "17.5cm")
        text_props.setdefault("y", "4.5cm")
        text_props.setdefault("width", f"{SLIDE_WIDTH - 17.5 - MARGIN}cm")
        text_props.setdefault("height", "12cm")
        run_officecli([
            "add", file_path, f"/slide[{slide_num}]",
            "--type", content[1].get("type", "shape")
        ] + format_props(text_props))

    return {"success": True, "slide_number": slide_num, "message": f"已添加第 {slide_num} 张幻灯片"}


@ToolRegistry.register("view_pptx")
def view_pptx(file_path: str, mode: str = "outline") -> dict[str, Any]:
    """
    查看 PPT 演示文稿的语义化视图。

    Args:
        file_path: PPT 文件路径。
        mode: 视图模式，可选 outline | stats | issues | text | html | screenshot | svg。
    """
    return run_officecli(["view", file_path, mode])


@ToolRegistry.register("get_pptx")
def get_pptx(file_path: str, path: str, depth: int | None = None) -> dict[str, Any]:
    """
    获取 PPT 中指定路径的元素 JSON。

    Args:
        file_path: PPT 文件路径。
        path: 元素路径，例如 /slide[1]、/slide[1]/shape[1]。
        depth: 展开子元素的深度。
    """
    args = ["get", file_path, path]
    if depth is not None:
        args.extend(["--depth", str(depth)])
    return run_officecli(args)


@ToolRegistry.register("query_pptx")
def query_pptx(file_path: str, selector: str) -> dict[str, Any]:
    """
    使用 CSS-like 选择器查询 PPT 元素。

    Args:
        file_path: PPT 文件路径。
        selector: 选择器，例如 "shape[fill=FF0000]"、"slide:has(shape:contains(Q4))".
    """
    return run_officecli(["query", file_path, selector])


@ToolRegistry.register("set_pptx")
def set_pptx(
    file_path: str,
    path: str,
    props: dict[str, Any] | None = None,
    find: str | None = None,
    replace: str | None = None,
) -> dict[str, Any]:
    """
    修改 PPT 中指定路径的元素。

    Args:
        file_path: PPT 文件路径。
        path: 元素路径，例如 /slide[1]/shape[1]。
        props: 属性字典，例如 {"text": "新标题", "x": "2cm", "y": "5cm", "fill": "1A1A2E"}。
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


@ToolRegistry.register("add_pptx")
def add_pptx(
    file_path: str,
    parent: str,
    element_type: str,
    props: dict[str, Any] | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """
    在 PPT 演示文稿中添加新元素。

    Args:
        file_path: PPT 文件路径。
        parent: 父节点路径，例如 /、/slide[1]。
        element_type: 元素类型，例如 slide、shape、picture、chart、table、textbox。
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


@ToolRegistry.register("remove_pptx")
def remove_pptx(file_path: str, path: str) -> dict[str, Any]:
    """删除 PPT 中指定路径的元素。"""
    return run_officecli(["remove", file_path, path])


@ToolRegistry.register("move_pptx")
def move_pptx(
    file_path: str,
    path: str,
    to: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """移动 PPT 中的元素到新位置。"""
    args = ["move", file_path, path]
    if to is not None:
        args.extend(["--to", to])
    if after is not None:
        args.extend(["--after", after])
    if before is not None:
        args.extend(["--before", before])
    return run_officecli(args)


@ToolRegistry.register("swap_pptx")
def swap_pptx(file_path: str, path1: str, path2: str) -> dict[str, Any]:
    """交换 PPT 中两个元素的位置。"""
    return run_officecli(["swap", file_path, path1, path2])


@ToolRegistry.register("raw_pptx")
def raw_pptx(file_path: str, part: str = "/ppt/presentation") -> dict[str, Any]:
    """查看 PPT 的原始 XML（兜底方案）。"""
    return run_officecli(["raw", file_path, part], expect_json=False)


@ToolRegistry.register("raw_set_pptx")
def raw_set_pptx(
    file_path: str,
    part: str,
    xpath: str,
    action: str,
    xml: str | None = None,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """直接修改 PPT 的原始 XML（兜底方案）。"""
    args = ["raw-set", file_path, part, xpath, action]
    if xml is not None:
        args.extend(["--xml", xml])
    args.extend(format_props(props))
    return run_officecli(args)


@ToolRegistry.register("validate_pptx")
def validate_pptx(file_path: str) -> dict[str, Any]:
    """验证 PPT 是否符合 OpenXML 规范。"""
    return run_officecli(["validate", file_path])


@ToolRegistry.register("batch_pptx")
def batch_pptx(file_path: str, commands: list[dict[str, Any]]) -> dict[str, Any]:
    """批量执行多个 PPT 操作（性能优化）。"""
    import json

    commands_json = json.dumps(commands)
    return run_officecli(["batch", file_path, "--commands", commands_json])


@ToolRegistry.register("clear_pptx")
def clear_pptx(file_path: str) -> dict[str, Any]:
    """
    清空 PPT 演示文稿的所有幻灯片。

    删除所有幻灯片，但保留演示文稿结构。适用于需要完全重写内容的场景。

    Args:
        file_path: PPT 文件路径。

    Returns:
        操作结果。
    """
    import json

    # 查询所有幻灯片
    result = run_officecli(["query", file_path, "slide"])
    if not result.get("success") or not result.get("data"):
        return {"success": True, "message": "演示文稿已为空"}

    # 从 results 字段提取路径
    data = result["data"]
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
        paths = [item.get("path") for item in results if isinstance(item, dict) and item.get("path")]
    else:
        paths = []

    if not paths:
        return {"success": True, "message": "演示文稿已为空"}

    commands = [{"command": "remove", "path": path} for path in paths]
    return run_officecli(["batch", file_path, "--commands", json.dumps(commands)])


@ToolRegistry.register("replace_pptx")
def replace_pptx(file_path: str, new_content: list[dict[str, Any]]) -> dict[str, Any]:
    """
    用新内容完全替换 PPT 演示文稿的所有内容。

    先清空演示文稿，然后批量添加新内容。适用于需要完全重写内容的场景。

    Args:
        file_path: PPT 文件路径。
        new_content: 新内容列表，每个元素是一个字典，包含 type 和 props。
                     例如：[{"type": "slide", "props": {"layout": "Title"}}]

    Returns:
        操作结果。
    """
    import json

    # 先清空
    clear_result = clear_pptx(file_path)
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
    return {"success": True, "message": "演示文稿已清空"}


@ToolRegistry.register("merge_document")
def merge_document(template_path: str, output_path: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    使用 JSON 数据填充 Office 模板中的 {{key}} 占位符。

    Args:
        template_path: 模板文件路径（.docx/.xlsx/.pptx）。
        output_path: 输出文件路径。
        data: 占位符数据，例如 {"client": "Acme", "total": "$5,200"}。

    Returns:
        操作结果。
    """
    import json

    data_json = json.dumps(data)
    return run_officecli(["merge", template_path, output_path, data_json])


@ToolRegistry.register("office_help")
def office_help(fmt: str, element: str | None = None, verb: str | None = None) -> dict[str, Any]:
    """
    查询 officecli 的属性/命令帮助。当不确定属性名或命令语法时使用。

    Args:
        fmt: 格式，可选 docx | xlsx | pptx | word | excel | ppt | powerpoint。
        element: 元素类型，例如 paragraph、shape、cell。
        verb: 动词过滤，例如 set、add、query。

    Returns:
        帮助文本或结构化 schema。
    """
    args = ["help", fmt]
    if verb is not None:
        args.append(verb)
    if element is not None:
        args.append(element)
    return run_officecli(args, expect_json=False)
