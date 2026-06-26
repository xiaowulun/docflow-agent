"""
Confirmation Gate - 确认闸门

任何写入操作执行前，必须通过确认闸门。
闸门会暂停流程，等待用户确认后才继续。

规则：
- 计划中有写入/导出操作时，必须暂停等待确认
- 计划以文字形式展示给用户
- 不确定项必须显式列出
"""

from packages.schemas.plan import ExecutionPlan


class ConfirmationGate:
    """确认闸门"""

    @staticmethod
    def format_plan_for_display(plan: ExecutionPlan) -> str:
        """
        将执行计划格式化为人类可读的文本，用于展示给用户。

        Args:
            plan: 执行计划

        Returns:
            格式化的文本
        """
        lines = []
        lines.append(f"## 执行计划")
        lines.append(f"**意图**: {plan.intent}")
        lines.append("")
        lines.append("### 操作步骤:")
        for i, action in enumerate(plan.actions, 1):
            confirm_mark = "⚠️ 需确认" if action.requires_confirmation else "✅ 自动执行"
            lines.append(f"{i}. [{confirm_mark}] {action.description}")
            if action.params:
                lines.append(f"   参数: {action.params}")
        lines.append("")

        if plan.uncertainties:
            lines.append("### ⚠️ 不确定项:")
            for item in plan.uncertainties:
                lines.append(f"- {item}")
            lines.append("")

        if plan.expected_output:
            lines.append(f"### 预期输出:")
            lines.append(plan.expected_output)

        return "\n".join(lines)

    @staticmethod
    def needs_confirmation(plan: ExecutionPlan) -> bool:
        """检查计划是否需要用户确认"""
        return plan.needs_confirmation()

    @staticmethod
    def confirm(plan: ExecutionPlan) -> ExecutionPlan:
        """
        用户确认后，返回计划（可以在此处添加确认后的处理逻辑）。

        Args:
            plan: 待确认的计划

        Returns:
            确认后的计划
        """
        return plan

    @staticmethod
    def reject(plan: ExecutionPlan) -> None:
        """用户拒绝计划"""
        raise ValueError("Plan rejected by user")
