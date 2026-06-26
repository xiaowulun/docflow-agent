"""
Word 文档工具

提供 Word 文档的读取、结构提取、按锚点写入、模板填充等功能。
"""

from packages.tooling.word.reader import read_docx, extract_docx_structure
from packages.tooling.word.writer import insert_text_by_anchor, fill_template_fields

__all__ = [
    "read_docx",
    "extract_docx_structure",
    "insert_text_by_anchor",
    "fill_template_fields",
]
