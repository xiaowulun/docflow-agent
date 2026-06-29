"""
Tooling 包

文档处理工具层，通过 registry 统一注册和调用。
- officecli/: OfficeCLI 封装（Word/Excel/PPT 完整操作）
"""

# 导入 officecli 子模块以触发工具注册
from packages.tooling.officecli import docx, pptx, session, xlsx  # noqa: F401
from packages.tooling.registry import ToolRegistry

__all__ = ["ToolRegistry"]
