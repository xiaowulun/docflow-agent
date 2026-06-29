"""
OfficeCLI 底层封装

负责检测 officecli 二进制、执行命令、解析 JSON 输出和统一错误处理。
所有调用默认追加 --json 以获得结构化输出。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_OFFICECLI_BIN: str | None = None


def find_binary() -> str | None:
    """在 PATH 或常见安装位置查找 officecli 二进制。"""
    global _OFFICECLI_BIN

    if _OFFICECLI_BIN is not None:
        return _OFFICECLI_BIN

    # 优先 PATH
    found = shutil.which("officecli")
    if found:
        _OFFICECLI_BIN = found
        return found

    # 常见安装位置
    home = Path.home()
    candidates = [
        home / ".officecli" / "officecli",
        home / ".local" / "bin" / "officecli",
        Path("/usr/local/bin/officecli"),
        Path("/opt/officecli/officecli"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            _OFFICECLI_BIN = str(candidate)
            return _OFFICECLI_BIN

    return None


def is_available() -> bool:
    """判断 officecli 是否可用。"""
    return find_binary() is not None


def _clean_env() -> dict[str, str]:
    """构造无代理污染的子进程环境，避免 officecli 下载阶段受本地代理影响。"""
    env = os.environ.copy()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        env.pop(key, None)
    # 允许 batch 命令在 stdin 重定向时正常工作
    env["OFFICECLI_BATCH_ALLOW_STDIN_REDIRECT"] = "1"
    return env


def run_officecli(
    args: list[str],
    *,
    timeout: int = 60,
    expect_json: bool = True,
) -> dict[str, Any]:
    """
    执行 officecli 命令并返回结构化结果。

    Args:
        args: officecli 子命令参数，不含二进制名。
        timeout: 命令超时时间（秒）。
        expect_json: 是否自动追加 --json 并解析 JSON。

    Returns:
        解析后的 JSON dict，或 stdout 文本包装 dict（expect_json=False 时）。

    Raises:
        RuntimeError: 未找到 officecli 二进制。
        OfficeCLIError: 命令执行失败或输出无法解析。
    """
    binary = find_binary()
    if binary is None:
        raise RuntimeError(
            "未找到 officecli 二进制。请先运行官方安装脚本："
            "curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash"  # noqa: E501
        )

    cmd = [binary] + args
    if expect_json and "--json" not in args:
        cmd.append("--json")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_clean_env(),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise OfficeCLIError(f"officecli 执行超时 ({timeout}s): {' '.join(cmd)}") from exc

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise OfficeCLIError(f"officecli 失败: {err}")

    if not expect_json:
        return {"stdout": result.stdout.strip()}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise OfficeCLIError(
            f"无法解析 officecli JSON 输出: {exc}\n原始输出:\n{result.stdout[:500]}"
        ) from exc


class OfficeCLIError(Exception):
    """OfficeCLI 调用异常。"""


def format_props(props: dict[str, Any] | None) -> list[str]:
    """将字典形式的属性转换为 officecli 的 --prop key=value 参数列表。"""
    if not props:
        return []
    args: list[str] = []
    for key, value in props.items():
        args.extend(["--prop", f"{key}={value}"])
    return args
