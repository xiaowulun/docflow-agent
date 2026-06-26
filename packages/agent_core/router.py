"""
Router - 任务类型判断

根据用户输入和文件类型，判断任务属于哪种类型。
决定后续走哪个 Analyzer 和工具链。
"""

from packages.schemas.file import FileType
from packages.schemas.task import TaskType


def classify_task(user_input: str, file_type: FileType) -> TaskType:
    """
    根据用户输入和文件类型判断任务类型。

    Args:
        user_input: 用户的自然语言指令
        file_type: 上传文件的类型

    Returns:
        TaskType 枚举值
    """
    input_lower = user_input.lower()

    # 关键词匹配
    read_keywords = ["读取", "提取", "查看", "读", "获取", "解析", "分析"]
    write_keywords = ["写入", "填充", "替换", "修改", "填写", "插入", "更新"]
    export_keywords = ["导出", "生成", "输出", "转换"]

    is_read = any(kw in input_lower for kw in read_keywords)
    is_write = any(kw in input_lower for kw in write_keywords)
    is_export = any(kw in input_lower for kw in export_keywords)

    if file_type == FileType.WORD:
        if is_write:
            return TaskType.WORD_WRITE
        return TaskType.WORD_READ

    elif file_type == FileType.EXCEL:
        if is_write:
            return TaskType.EXCEL_WRITE
        return TaskType.EXCEL_READ

    elif file_type == FileType.PDF:
        if is_export:
            return TaskType.PDF_EXPORT
        return TaskType.PDF_READ

    return TaskType.UNKNOWN
