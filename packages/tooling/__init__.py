"""
Tooling 包

文档处理工具层，通过 registry 统一注册和调用。
- word/: Word 文档读写
- excel/: Excel 表格读写
- pdf/: PDF 读取和导出
- ocr/: OCR 接口（预留）
"""

from packages.tooling.registry import ToolRegistry

__all__ = ["ToolRegistry"]
