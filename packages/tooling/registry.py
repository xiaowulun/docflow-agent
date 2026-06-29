"""
工具注册中心

所有文档处理工具通过装饰器注册到 ToolRegistry。
Executor 通过 registry.get(name) 获取工具并调用。

使用示例：
    @ToolRegistry.register("read_docx")
    def read_docx(path: str) -> dict:
        ...
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ToolRegistry:
    """工具注册中心"""

    _tools: dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """装饰器，注册工具到 registry"""

        def wrapper(func: Callable) -> Callable:
            cls._tools[name] = func
            return func

        return wrapper

    @classmethod
    def get(cls, name: str) -> Callable | None:
        """根据名称获取工具"""
        return cls._tools.get(name)

    @classmethod
    def call(cls, name: str, **kwargs) -> Any:
        """调用工具"""
        tool = cls.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found in registry")
        return tool(**kwargs)

    @classmethod
    def list_tools(cls) -> list[str]:
        """列出所有已注册的工具名"""
        return list(cls._tools.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """检查工具是否存在"""
        return name in cls._tools
