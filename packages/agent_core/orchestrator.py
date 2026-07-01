"""
Orchestrator - 编排器

串联整个 agent 流程：
    upload -> analyze -> plan -> await_confirm -> execute -> verify -> done/failed

负责：
- 管理任务状态流转
- 调用各模块完成处理
- 记录审计事件
"""

from datetime import datetime

from packages.agent_core.analyzer import analyze_file
from packages.agent_core.confirmation_gate import ConfirmationGate
from packages.agent_core.executor import Executor
from packages.agent_core.planner import generate_plan
from packages.agent_core.router import classify_task
from packages.agent_core.state_machine import validate_transition
from packages.agent_core.verifier import verify_results
from packages.schemas.events import EventType, TaskAuditLog
from packages.schemas.file import FileInfo
from packages.schemas.plan import ExecutionPlan
from packages.schemas.task import (
    ConfirmationKind,
    ConfirmationRequest,
    ConfirmationStage,
    Task,
    TaskStatus,
)


class Orchestrator:
    """
    编排器，驱动整个任务流程。

    使用方式：
        orchestrator = Orchestrator()
        task = orchestrator.start(file_path, user_input)
        plan = orchestrator.analyze_and_plan(task.task_id)
        orchestrator.confirm(task.task_id)
        result = orchestrator.execute(task.task_id)
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._plans: dict[str, ExecutionPlan] = {}
        self._audit_logs: dict[str, TaskAuditLog] = {}
        self._executor = Executor()

    def start(self, file_path: str, user_input: str) -> Task:
        """
        开始新任务。

        Args:
            file_path: 上传的文件路径
            user_input: 用户指令

        Returns:
            Task 任务对象
        """
        # 创建文件信息
        file_info = FileInfo.from_path(file_path)

        # 创建任务
        task = Task(
            user_input=user_input,
            file_paths=[file_path],
        )

        # 创建审计日志
        audit_log = TaskAuditLog(task_id=task.task_id)

        # 存储
        self._tasks[task.task_id] = task
        self._audit_logs[task.task_id] = audit_log

        # 记录事件
        audit_log.add_event(
            EventType.TASK_CREATED,
            actor="user",
            file_path=file_path,
            user_input=user_input,
        )
        audit_log.add_event(
            EventType.FILE_UPLOADED,
            actor="system",
            filename=file_info.filename,
            file_type=file_info.file_type.value,
        )

        return task

    def analyze_and_plan(self, task_id: str) -> ExecutionPlan:
        """
        分析文件并生成计划。

        Args:
            task_id: 任务 ID

        Returns:
            ExecutionPlan 执行计划
        """
        task = self._tasks[task_id]
        audit_log = self._audit_logs[task_id]

        # 状态: * -> analyzing
        if task.status != TaskStatus.ANALYZING:
            validate_transition(task.status, TaskStatus.ANALYZING)
            task.update_status(TaskStatus.ANALYZING)
        audit_log.add_event(EventType.ANALYSIS_STARTED)

        # 分析文件
        file_info = FileInfo.from_path(task.file_paths[0])
        analysis = analyze_file(file_info)
        audit_log.add_event(EventType.ANALYSIS_DONE)

        if analysis.ambiguities:
            request = ConfirmationGate.build_ambiguity_request(
                analysis.ambiguities,
                stage=ConfirmationStage.ANALYZING,
                resume_from="analysis",
            )
            self._set_confirmation_request(task, audit_log, request)
            # 这里先返回一个空计划占位，后续待用户补充信息后重试分析/规划。
            plan = ExecutionPlan(
                task_id=task.task_id,
                intent="等待人工消解歧义",
                uncertainties=list(analysis.ambiguities),
            )
            self._plans[task_id] = plan
            return plan

        # 判断任务类型
        task_type = classify_task(task.user_input, file_info.file_type)
        task.task_type = task_type

        # 生成计划
        plan = generate_plan(task_type, analysis, task.user_input)
        self._plans[task_id] = plan

        # 状态: analyzing -> planned
        validate_transition(task.status, TaskStatus.PLANNED)
        task.update_status(TaskStatus.PLANNED)
        audit_log.add_event(EventType.PLAN_GENERATED, plan_id=plan.plan_id)

        # 如果需要确认，进入等待状态
        if plan.uncertainties:
            request = ConfirmationGate.build_ambiguity_request(
                plan.uncertainties,
                stage=ConfirmationStage.PLANNED,
                resume_from="planning",
            )
            self._set_confirmation_request(task, audit_log, request)
        elif ConfirmationGate.needs_confirmation(plan):
            request = ConfirmationGate.build_plan_review_request(plan)
            self._set_confirmation_request(task, audit_log, request)

        return plan

    def get_plan_display(self, task_id: str) -> str:
        """获取计划的展示文本"""
        plan = self._plans[task_id]
        return ConfirmationGate.format_plan_for_display(plan)

    def confirm(self, task_id: str) -> ConfirmationRequest | None:
        """
        用户确认计划。

        Args:
            task_id: 任务 ID
        """
        task = self._tasks[task_id]
        audit_log = self._audit_logs[task_id]
        request = task.confirmation_request

        if request is None:
            raise ValueError("Task is not waiting for confirmation")

        next_status = self._resolve_post_confirm_status(request)
        validate_transition(task.status, next_status)
        task.set_confirmation_request(None)
        task.update_status(next_status)
        audit_log.add_event(
            EventType.CONFIRMATION_GIVEN,
            actor="user",
            request_kind=request.kind.value,
            resume_to=next_status.value,
        )
        return request

    def reject_confirmation(self, task_id: str) -> ConfirmationRequest | None:
        """用户拒绝当前确认请求"""
        task = self._tasks[task_id]
        audit_log = self._audit_logs[task_id]
        request = task.confirmation_request

        if request is None:
            raise ValueError("Task is not waiting for confirmation")

        task.set_confirmation_request(None)
        validate_transition(task.status, TaskStatus.FAILED)
        task.update_status(TaskStatus.FAILED)
        task.error_message = f"Confirmation rejected: {request.kind.value}"
        audit_log.add_event(
            EventType.CONFIRMATION_REJECTED,
            actor="user",
            request_kind=request.kind.value,
        )
        audit_log.add_event(EventType.TASK_FAILED, error=task.error_message)
        return request

    def execute(self, task_id: str) -> dict:
        """
        执行计划并校验结果。

        Args:
            task_id: 任务 ID

        Returns:
            执行结果摘要
        """
        task = self._tasks[task_id]
        plan = self._plans[task_id]
        audit_log = self._audit_logs[task_id]

        if task.confirmation_request is not None:
            raise ValueError("Task is still waiting for confirmation")

        if task.status != TaskStatus.EXECUTING:
            validate_transition(task.status, TaskStatus.EXECUTING)
            task.update_status(TaskStatus.EXECUTING)

        # 记录执行开始
        audit_log.add_event(EventType.EXECUTION_STARTED)

        # 执行
        exec_results = self._executor.execute_plan(plan)

        for er in exec_results:
            audit_log.add_event(
                EventType.ACTION_EXECUTED,
                action_id=er.action.action_id,
                tool_name=er.action.tool_name,
                success=er.success,
            )

        # 检查是否有失败
        if any(not er.success for er in exec_results):
            validate_transition(task.status, TaskStatus.FAILED)
            task.update_status(TaskStatus.FAILED)
            task.error_message = next(
                er.error for er in exec_results if not er.success
            )
            audit_log.add_event(EventType.TASK_FAILED, error=task.error_message)
            return {"success": False, "error": task.error_message}

        # 状态: executing -> verifying
        validate_transition(task.status, TaskStatus.VERIFYING)
        task.update_status(TaskStatus.VERIFYING)
        audit_log.add_event(EventType.EXECUTION_DONE)

        # 校验
        audit_log.add_event(EventType.VERIFICATION_STARTED)
        verification = verify_results(plan, exec_results)
        audit_log.add_event(EventType.VERIFICATION_DONE, **verification.to_dict())

        if verification.passed:
            validate_transition(task.status, TaskStatus.DONE)
            task.update_status(TaskStatus.DONE)
            audit_log.add_event(EventType.TASK_COMPLETED)
        else:
            validate_transition(task.status, TaskStatus.FAILED)
            task.update_status(TaskStatus.FAILED)
            task.error_message = "Verification failed"
            audit_log.add_event(EventType.TASK_FAILED, error=task.error_message)

        return {
            "success": verification.passed,
            "verification": verification.to_dict(),
            "execution_results": [er.to_dict() for er in exec_results],
        }

    def get_task(self, task_id: str) -> Task | None:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_audit_log(self, task_id: str) -> TaskAuditLog | None:
        """获取审计日志"""
        return self._audit_logs.get(task_id)

    def _set_confirmation_request(
        self,
        task: Task,
        audit_log: TaskAuditLog,
        request: ConfirmationRequest,
    ) -> None:
        """将任务置为等待确认，并记录确认请求"""
        validate_transition(task.status, TaskStatus.AWAITING_CONFIRM)
        task.set_confirmation_request(request)
        task.update_status(TaskStatus.AWAITING_CONFIRM)
        audit_log.add_event(
            EventType.CONFIRMATION_REQUESTED,
            request_id=request.request_id,
            request_kind=request.kind.value,
            request_stage=request.stage.value,
            resume_from=request.resume_from,
        )

    @staticmethod
    def _resolve_post_confirm_status(request: ConfirmationRequest) -> TaskStatus:
        """根据确认请求类型决定确认后回到哪个状态"""
        if request.kind == ConfirmationKind.AMBIGUITY_RESOLUTION:
            return TaskStatus.ANALYZING
        return TaskStatus.EXECUTING

    def resume(self, task_id: str, user_input: str | None = None) -> ExecutionPlan:
        """在确认后继续推进任务，必要时带上新的用户补充说明"""
        task = self._tasks[task_id]

        if user_input and user_input.strip():
            task.user_input = user_input.strip()
            task.updated_at = datetime.now()

        return self.analyze_and_plan(task_id)
