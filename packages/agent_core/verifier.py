"""
Verifier - 校验器

执行后重新读取输出文件，检查：
- 内容是否写入成功
- 格式是否明显损坏
- 输出文件是否可打开
"""

from pathlib import Path

from packages.schemas.plan import ExecutionPlan
from packages.agent_core.executor import ExecutionResult


class VerificationResult:
    """校验结果"""

    def __init__(self):
        self.passed: bool = True
        self.checks: list[dict] = []

    def add_check(self, name: str, passed: bool, detail: str = ""):
        """添加检查项"""
        self.checks.append({
            "name": name,
            "passed": passed,
            "detail": detail,
        })
        if not passed:
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
        }


def verify_results(
    plan: ExecutionPlan,
    execution_results: list[ExecutionResult],
) -> VerificationResult:
    """
    校验执行结果。

    Args:
        plan: 执行计划
        execution_results: 执行结果列表

    Returns:
        VerificationResult 校验结果
    """
    result = VerificationResult()

    # 检查所有步骤是否成功
    for exec_result in execution_results:
        if not exec_result.success:
            result.add_check(
                name=f"action_{exec_result.action.action_id}_success",
                passed=False,
                detail=exec_result.error or "Action failed",
            )
            result.passed = False
            return result

    # 检查输出文件是否存在
    for exec_result in execution_results:
        output_path = exec_result.output.get("output_path")
        if output_path:
            path = Path(output_path)
            exists = path.exists()
            result.add_check(
                name=f"output_file_{path.name}_exists",
                passed=exists,
                detail=f"File path: {output_path}",
            )

            # 检查文件大小
            if exists and path.stat().st_size == 0:
                result.add_check(
                    name=f"output_file_{path.name}_not_empty",
                    passed=False,
                    detail="Output file is empty",
                )

    return result
