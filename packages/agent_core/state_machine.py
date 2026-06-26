"""
状态机

定义任务状态流转规则，校验状态转换是否合法。
状态流转：
    created -> analyzing -> planned -> awaiting_confirm -> executing -> verifying -> done / failed
"""

from packages.schemas.task import TaskStatus

# 合法的状态转换映射
VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.CREATED: [TaskStatus.ANALYZING, TaskStatus.FAILED],
    TaskStatus.ANALYZING: [TaskStatus.PLANNED, TaskStatus.FAILED],
    TaskStatus.PLANNED: [TaskStatus.AWAITING_CONFIRM, TaskStatus.FAILED],
    TaskStatus.AWAITING_CONFIRM: [TaskStatus.EXECUTING, TaskStatus.FAILED],
    TaskStatus.EXECUTING: [TaskStatus.VERIFYING, TaskStatus.FAILED],
    TaskStatus.VERIFYING: [TaskStatus.DONE, TaskStatus.FAILED],
    TaskStatus.DONE: [],  # 终态
    TaskStatus.FAILED: [],  # 终态
}


class InvalidTransitionError(Exception):
    """非法状态转换异常"""

    def __init__(self, current: TaskStatus, target: TaskStatus):
        self.current = current
        self.target = target
        super().__init__(f"Invalid transition: {current.value} -> {target.value}")


def validate_transition(current: TaskStatus, target: TaskStatus) -> None:
    """校验状态转换是否合法，不合法则抛异常"""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidTransitionError(current, target)


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    """检查状态转换是否合法（不抛异常）"""
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed
