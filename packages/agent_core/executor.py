"""
Executor - 执行器

确认后执行具体工具调用。
要求：
- 尽量走确定性参数，不让模型临场发挥
- 每个 Action 调用对应的工具
- 记录执行结果
"""

from packages.schemas.plan import Action, ExecutionPlan
from packages.tooling.registry import ToolRegistry


class ExecutionResult:
    """单个 Action 的执行结果"""

    def __init__(self, action: Action):
        self.action = action
        self.success: bool = False
        self.output: dict = {}
        self.error: str | None = None

    def to_dict(self) -> dict:
        return {
            "action_id": self.action.action_id,
            "tool_name": self.action.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


class Executor:
    """执行器"""

    def execute_plan(self, plan: ExecutionPlan) -> list[ExecutionResult]:
        """
        按顺序执行计划中的所有操作。

        Args:
            plan: 已确认的执行计划

        Returns:
            每个 Action 的执行结果列表
        """
        results = []

        for action in plan.actions:
            result = self._execute_action(action)
            results.append(result)

            # 如果某个步骤失败，后续步骤跳过
            if not result.success:
                break

        return results

    def _execute_action(self, action: Action) -> ExecutionResult:
        """执行单个 Action"""
        result = ExecutionResult(action)

        try:
            tool = ToolRegistry.get(action.tool_name)
            if tool is None:
                result.error = f"Tool '{action.tool_name}' not found"
                return result

            output = tool(**action.params)
            result.success = True
            result.output = output if isinstance(output, dict) else {"result": output}

        except Exception as e:
            result.error = str(e)

        return result
