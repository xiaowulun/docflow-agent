"""
Analyzer - 文件分析器

只读分析输入文件，提取：
- 文本内容
- 文档结构（标题、段落）
- 可填充字段
- 锚点位置
- 文件元信息

不修改任何文件。
"""

from pathlib import Path

from packages.schemas.file import FileAnalysis, FileInfo, FileType
from packages.tooling.registry import ToolRegistry


def analyze_file(file_info: FileInfo) -> FileAnalysis:
    """
    分析文件，返回结构化信息。

    Args:
        file_info: 文件元信息

    Returns:
        FileAnalysis 分析结果
    """
    analysis = FileAnalysis(file_info=file_info)
    path = file_info.file_path

    if file_info.file_type == FileType.WORD:
        analysis = _analyze_word(path, analysis)
    elif file_info.file_type == FileType.EXCEL:
        analysis = _analyze_excel(path, analysis)
    elif file_info.file_type == FileType.PDF:
        analysis = _analyze_pdf(path, analysis)

    return analysis


def _analyze_word(path: str, analysis: FileAnalysis) -> FileAnalysis:
    """分析 Word 文档"""
    if ToolRegistry.has("read_docx"):
        content = ToolRegistry.call("read_docx", path=path)
        analysis.text_content = content.get("text", "")
        analysis.structure = content.get("structure", {})
        analysis.anchors = content.get("anchors", [])
    return analysis


def _analyze_excel(path: str, analysis: FileAnalysis) -> FileAnalysis:
    """分析 Excel 文件"""
    if ToolRegistry.has("read_xlsx"):
        content = ToolRegistry.call("read_xlsx", path=path)
        analysis.sheet_names = content.get("sheet_names", [])
        analysis.structure = content.get("structure", {})
    return analysis


def _analyze_pdf(path: str, analysis: FileAnalysis) -> FileAnalysis:
    """分析 PDF 文件"""
    if ToolRegistry.has("read_pdf_text"):
        content = ToolRegistry.call("read_pdf_text", path=path)
        analysis.text_content = content.get("text", "")
        analysis.page_count = content.get("page_count", 0)
    return analysis
