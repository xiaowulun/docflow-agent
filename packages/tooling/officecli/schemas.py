"""
OfficeCLI 工具的 OpenAI function schema。

这些 schema 供 LLM 理解每个工具的用途和参数。
"""


def _create_schema(fmt: str, ext: str) -> dict:
    name = f"create_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"创建一个空白 {ext.upper()} ({ext}) 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": f"目标文件路径，必须以 .{ext} 结尾。",
                    }
                },
                "required": ["path"],
            },
        },
    }


def _view_schema(fmt: str, ext: str, modes: str) -> dict:
    name = f"view_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"查看 {ext.upper()} 文档的语义化视图。适用模式：{modes}。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "mode": {
                        "type": "string",
                        "description": f"视图模式，可选 {modes}，默认 outline。",
                    },
                },
                "required": ["file_path"],
            },
        },
    }


def _get_schema(fmt: str, ext: str) -> dict:
    name = f"get_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"获取 {ext.upper()} 文档中指定路径的元素 JSON。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "元素路径，例如 /body/p[1]、/slide[1]/shape[1]、/Sheet1/A1。"
                            "当 watch 预览已启动时，也可使用 selected 读取当前浏览器选中的元素。"
                        ),
                    },
                    "depth": {
                        "type": "integer",
                        "description": "展开子元素的深度，可选。",
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    }


def _query_schema(fmt: str, ext: str) -> dict:
    name = f"query_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"使用 CSS-like 选择器查询 {ext.upper()} 文档元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "selector": {
                        "type": "string",
                        "description": (
                            "CSS-like 选择器，例如 paragraph[style=Heading1]、"
                            "shape[fill=FF0000]、cell[value>5000]。"
                        ),
                    },
                },
                "required": ["file_path", "selector"],
            },
        },
    }


def _set_schema(fmt: str, ext: str) -> dict:
    name = f"set_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"修改 {ext.upper()} 文档中指定路径的元素属性或文本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "元素路径。例如 /body/p[1]、/slide[1]/shape[1]、/Sheet1/A1。"
                        ),
                    },
                    "props": {
                        "type": "object",
                        "description": (
                            '属性字典，例如 {"text": "新标题", "bold": "true", "value": "100"}。'
                        ),
                    },
                    "find": {
                        "type": "string",
                        "description": "可选，要查找的文本片段。",
                    },
                    "replace": {
                        "type": "string",
                        "description": "可选，要替换成的文本。",
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    }


def _add_schema(fmt: str, ext: str) -> dict:
    name = f"add_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"在 {ext.upper()} 文档指定父节点下添加新元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "parent": {
                        "type": "string",
                        "description": "父节点路径，例如 /body、/、/slide[1]、/Sheet1。",
                    },
                    "element_type": {
                        "type": "string",
                        "description": (
                            "元素类型，例如 paragraph、shape、cell、slide、chart、table。"
                        ),
                    },
                    "props": {
                        "type": "object",
                        "description": "元素属性字典。",
                    },
                    "after": {
                        "type": "string",
                        "description": "可选，插入到该路径之后。",
                    },
                    "before": {
                        "type": "string",
                        "description": "可选，插入到该路径之前。",
                    },
                },
                "required": ["file_path", "parent", "element_type"],
            },
        },
    }


def _remove_schema(fmt: str, ext: str) -> dict:
    name = f"remove_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"删除 {ext.upper()} 文档中指定路径的元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "要删除的元素路径。",
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    }


OFFICECLI_SCHEMAS = [
    _create_schema("docx", "docx"),
    _create_schema("xlsx", "xlsx"),
    _create_schema("pptx", "pptx"),
    _view_schema("docx", "docx", "outline | stats | issues | text | annotated | html"),
    _view_schema("xlsx", "xlsx", "text | outline | stats | issues | html"),
    _view_schema("pptx", "pptx", "outline | stats | issues | text | html | screenshot | svg"),
    _get_schema("docx", "docx"),
    _get_schema("xlsx", "xlsx"),
    _get_schema("pptx", "pptx"),
    _query_schema("docx", "docx"),
    _query_schema("xlsx", "xlsx"),
    _query_schema("pptx", "pptx"),
    _set_schema("docx", "docx"),
    _set_schema("xlsx", "xlsx"),
    _set_schema("pptx", "pptx"),
    _add_schema("docx", "docx"),
    _add_schema("xlsx", "xlsx"),
    _add_schema("pptx", "pptx"),
    _remove_schema("docx", "docx"),
    _remove_schema("xlsx", "xlsx"),
    _remove_schema("pptx", "pptx"),
    {
        "type": "function",
        "function": {
            "name": "office_command",
            "description": (
                "透传调用 officecli 原生命令。用于访问当前项目未提供独立 wrapper 的官方能力。"
                "args 只传 officecli 子命令参数，不要包含 officecli 本身。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "description": '命令参数数组，例如 ["watch", "deck.pptx", "--port", "26315"]。',
                        "items": {"type": "string"},
                    },
                    "expect_json": {
                        "type": "boolean",
                        "description": "是否期望 JSON 输出，默认 true。",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒），默认 120。",
                    },
                },
                "required": ["args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "merge_document",
            "description": (
                "使用 JSON 数据填充 Office 模板中的 {{key}} 占位符，支持 .docx/.xlsx/.pptx。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "template_path": {
                        "type": "string",
                        "description": "模板文件路径。",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径。",
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            '占位符数据，例如 {"client": "Acme", "total": "$5,200"}。'
                        ),
                    },
                },
                "required": ["template_path", "output_path", "data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_help",
            "description": (
                "查询 officecli 的属性/命令帮助。当不确定属性名、取值格式或命令语法时必须优先使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fmt": {
                        "type": "string",
                        "description": (
                            "格式，可选 docx | xlsx | pptx | word | excel | ppt | powerpoint。"
                        ),
                    },
                    "element": {
                        "type": "string",
                        "description": "元素类型，例如 paragraph、shape、cell。",
                    },
                    "verb": {
                        "type": "string",
                        "description": "动词过滤，例如 set、add、query。",
                    },
                },
                "required": ["fmt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_watch",
            "description": "启动 Office 文档的实时预览服务，支持浏览器查看、选择、定位和后续 mark/goto。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    },
                    "port": {
                        "type": "integer",
                        "description": "预览服务端口，默认 26315。",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_unwatch",
            "description": "停止 Office 文档的实时预览服务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_mark",
            "description": "给 watch 预览中的元素添加内存标记，便于人工复核或后续批量修正。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "元素路径，也可传 selected 标记当前选中的元素。",
                    },
                    "props": {
                        "type": "object",
                        "description": '标记属性，如 {"color": "red", "note": "检查这里", "tofix": "tighten"}。',
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_unmark",
            "description": "删除 watch 预览中的元素标记。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "可选，指定要删除标记的元素路径。",
                    },
                    "remove_all": {
                        "type": "boolean",
                        "description": "是否删除当前文件的全部标记。",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_get_marks",
            "description": "列出 watch 预览中当前文件的全部标记。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_goto",
            "description": "让 watch 预览滚动定位到指定元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "要定位的元素路径。",
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_refresh",
            "description": "刷新派生字段，如目录页码、页码域、交叉引用等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    # 驻留模式
    {
        "type": "function",
        "function": {
            "name": "office_open",
            "description": "打开文档并保持在内存中（驻留模式），后续操作更快。使用完毕后必须调用 office_close。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_close",
            "description": "关闭驻留的文档，将内存中的更改刷新到磁盘并释放文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "office_save",
            "description": "将内存中的更改刷新到磁盘，但保持驻留模式继续运行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Office 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
]


def _move_schema(fmt: str, ext: str) -> dict:
    name = f"move_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"移动 {ext.upper()} 文档中的元素到新位置。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "要移动的元素路径。",
                    },
                    "to": {
                        "type": "string",
                        "description": "目标父节点路径。",
                    },
                    "after": {
                        "type": "string",
                        "description": "插入到该路径之后。",
                    },
                    "before": {
                        "type": "string",
                        "description": "插入到该路径之前。",
                    },
                },
                "required": ["file_path", "path"],
            },
        },
    }


def _swap_schema(fmt: str, ext: str) -> dict:
    name = f"swap_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"交换 {ext.upper()} 文档中两个元素的位置。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "path1": {
                        "type": "string",
                        "description": "第一个元素路径。",
                    },
                    "path2": {
                        "type": "string",
                        "description": "第二个元素路径。",
                    },
                },
                "required": ["file_path", "path1", "path2"],
            },
        },
    }


def _raw_schema(fmt: str, ext: str) -> dict:
    name = f"raw_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"查看 {ext.upper()} 文档的原始 XML（兜底方案）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "part": {
                        "type": "string",
                        "description": "文档部件路径，例如 /document、/styles。",
                    },
                },
                "required": ["file_path"],
            },
        },
    }


def _raw_set_schema(fmt: str, ext: str) -> dict:
    name = f"raw_set_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"直接修改 {ext.upper()} 文档的原始 XML（兜底方案）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "part": {
                        "type": "string",
                        "description": "文档部件路径。",
                    },
                    "xpath": {
                        "type": "string",
                        "description": "XPath 表达式定位要修改的元素。",
                    },
                    "action": {
                        "type": "string",
                        "description": "操作类型，可选 set-attr | add-child | remove。",
                    },
                    "xml": {
                        "type": "string",
                        "description": "要插入的 XML 片段（add-child 时使用）。",
                    },
                    "props": {
                        "type": "object",
                        "description": "属性字典（set-attr 时使用）。",
                    },
                },
                "required": ["file_path", "part", "xpath", "action"],
            },
        },
    }


def _validate_schema(fmt: str, ext: str) -> dict:
    name = f"validate_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"验证 {ext.upper()} 文档是否符合 OpenXML 规范。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    }


def _batch_schema(fmt: str, ext: str) -> dict:
    name = f"batch_{fmt}"
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"批量执行多个 {ext.upper()} 文档操作（性能优化）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": f"{ext.upper()} 文件路径。",
                    },
                    "commands": {
                        "type": "array",
                        "description": (
                            "命令列表，每个命令是一个字典。"
                            '例如：[{"command": "add", "parent": "/body", "type": "paragraph", "props": {"text": "Hello"}}]'
                        ),
                        "items": {
                            "type": "object",
                            "description": "单个命令，包含 command 字段和其他参数。",
                        },
                    },
                },
                "required": ["file_path", "commands"],
            },
        },
    }


# 添加 move/swap/raw/raw_set/validate/batch schema
OFFICECLI_SCHEMAS.extend([
    _move_schema("docx", "docx"),
    _move_schema("xlsx", "xlsx"),
    _move_schema("pptx", "pptx"),
    _swap_schema("docx", "docx"),
    _swap_schema("xlsx", "xlsx"),
    _swap_schema("pptx", "pptx"),
    _raw_schema("docx", "docx"),
    _raw_schema("xlsx", "xlsx"),
    _raw_schema("pptx", "pptx"),
    _raw_set_schema("docx", "docx"),
    _raw_set_schema("xlsx", "xlsx"),
    _raw_set_schema("pptx", "pptx"),
    _validate_schema("docx", "docx"),
    _validate_schema("xlsx", "xlsx"),
    _validate_schema("pptx", "pptx"),
    _batch_schema("docx", "docx"),
    _batch_schema("xlsx", "xlsx"),
    _batch_schema("pptx", "pptx"),
    {
        "type": "function",
        "function": {
            "name": "dump_docx",
            "description": "将 Word 文档或子树导出为可回放的 batch 脚本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Word 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "要导出的子树路径，默认 /。",
                    },
                    "format": {
                        "type": "string",
                        "description": "输出格式，当前通常为 batch。",
                    },
                    "out": {
                        "type": "string",
                        "description": "可选，写入目标文件。",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dump_pptx",
            "description": "将 PPT 文档或子树导出为可回放的 batch 脚本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PPT 文件路径。",
                    },
                    "path": {
                        "type": "string",
                        "description": "要导出的子树路径，默认 /。",
                    },
                    "format": {
                        "type": "string",
                        "description": "输出格式，当前通常为 batch。",
                    },
                    "out": {
                        "type": "string",
                        "description": "可选，写入目标文件。",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_part_docx",
            "description": "为 Word 文档创建新的部件，如 chart、header、footer，并返回关系 ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Word 文件路径。"},
                    "parent": {"type": "string", "description": "父部件路径，例如 /。"},
                    "part_type": {"type": "string", "description": "部件类型，如 chart、header、footer。"},
                },
                "required": ["file_path", "parent", "part_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_part_xlsx",
            "description": "为 Excel 工作簿创建新的部件，如 chart，并返回关系 ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Excel 文件路径。"},
                    "parent": {"type": "string", "description": "父部件路径，例如 /Sheet1。"},
                    "part_type": {"type": "string", "description": "部件类型，如 chart。"},
                },
                "required": ["file_path", "parent", "part_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_part_pptx",
            "description": "为 PPT 演示文稿创建新的部件，如 chart，并返回关系 ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "PPT 文件路径。"},
                    "parent": {"type": "string", "description": "父部件路径，例如 /slide[0]。"},
                    "part_type": {"type": "string", "description": "部件类型，如 chart。"},
                },
                "required": ["file_path", "parent", "part_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_xlsx",
            "description": "导入 CSV/TSV 数据到 Excel 工作表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel 文件路径。",
                    },
                    "parent_path": {
                        "type": "string",
                        "description": "目标工作表路径，例如 /Sheet1。",
                    },
                    "source_file": {
                        "type": "string",
                        "description": "源数据文件路径（CSV 或 TSV）。",
                    },
                    "format": {
                        "type": "string",
                        "description": "数据格式，可选 csv | tsv。",
                    },
                },
                "required": ["file_path", "parent_path", "source_file"],
            },
        },
    },
    # clear/replace 工具
    {
        "type": "function",
        "function": {
            "name": "clear_docx",
            "description": "清空 Word 文档的所有内容（保留文档结构）。适用于需要完全重写文档内容的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Word 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_docx",
            "description": "用新内容完全替换 Word 文档的所有内容。先清空文档，然后批量添加新内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Word 文件路径。",
                    },
                    "new_content": {
                        "type": "array",
                        "description": "新内容列表，每个元素包含 type 和 props。例如：[{\"type\": \"paragraph\", \"props\": {\"text\": \"新标题\", \"style\": \"Heading1\"}}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "props": {"type": "object"},
                            },
                        },
                    },
                },
                "required": ["file_path", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_xlsx",
            "description": "清空 Excel 工作簿的所有工作表内容。适用于需要完全重写内容的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_xlsx",
            "description": "用新内容完全替换 Excel 工作簿的所有内容。先清空工作簿，然后批量添加新内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel 文件路径。",
                    },
                    "new_content": {
                        "type": "array",
                        "description": "新内容列表，每个元素包含 type 和 props。例如：[{\"type\": \"sheet\", \"props\": {\"name\": \"Sheet1\"}}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "props": {"type": "object"},
                            },
                        },
                    },
                },
                "required": ["file_path", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_pptx",
            "description": "清空 PPT 演示文稿的所有幻灯片。适用于需要完全重写内容的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PPT 文件路径。",
                    }
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_pptx",
            "description": "用新内容完全替换 PPT 演示文稿的所有内容。先清空演示文稿，然后批量添加新内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PPT 文件路径。",
                    },
                    "new_content": {
                        "type": "array",
                        "description": "新内容列表，每个元素包含 type 和 props。例如：[{\"type\": \"slide\", \"props\": {\"layout\": \"Title\"}}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "props": {"type": "object"},
                            },
                        },
                    },
                },
                "required": ["file_path", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_pptx_slide_with_layout",
            "description": (
                "智能添加幻灯片，自动计算布局位置。推荐使用此工具而不是 add_pptx，因为它会自动处理元素的 x/y 坐标，避免内容堆叠在左上角。"
                "支持多种布局：title_only（仅标题）、title_content（标题+内容）、two_column（双栏）、image_text（图文）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PPT 文件路径。",
                    },
                    "title": {
                        "type": "string",
                        "description": "幻灯片标题。",
                    },
                    "content": {
                        "type": "array",
                        "description": (
                            "内容列表，每项包含 type 和 props。例如：[{\"type\": \"shape\", \"props\": {\"text\": \"内容文本\"}}]"
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "description": "元素类型，如 shape、picture"},
                                "props": {"type": "object", "description": "元素属性，如 {\"text\": \"文本内容\"}"},
                            },
                        },
                    },
                    "layout": {
                        "type": "string",
                        "description": "布局类型：title_only | title_content | two_column | image_text，默认 title_content。",
                        "enum": ["title_only", "title_content", "two_column", "image_text"],
                    },
                },
                "required": ["file_path", "title"],
            },
        },
    },
])
