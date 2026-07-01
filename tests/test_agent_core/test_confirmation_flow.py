from pathlib import Path

from packages.agent_core.confirmation_gate import ConfirmationGate
from packages.agent_core.orchestrator import Orchestrator
from packages.agent_core.state_machine import can_transition
from packages.schemas.file import FileAnalysis, FileInfo
from packages.schemas.plan import Action, ActionType, ExecutionPlan
from packages.schemas.task import (
    ConfirmationKind,
    ConfirmationStage,
    TaskStatus,
    TaskType,
)


def _make_file(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    path.write_text("stub", encoding="utf-8")
    return str(path)


def test_state_machine_allows_waiting_confirm_from_multiple_stages():
    assert can_transition(TaskStatus.ANALYZING, TaskStatus.AWAITING_CONFIRM)
    assert can_transition(TaskStatus.PLANNED, TaskStatus.AWAITING_CONFIRM)
    assert can_transition(TaskStatus.EXECUTING, TaskStatus.AWAITING_CONFIRM)

    assert can_transition(TaskStatus.AWAITING_CONFIRM, TaskStatus.ANALYZING)
    assert can_transition(TaskStatus.AWAITING_CONFIRM, TaskStatus.PLANNED)
    assert can_transition(TaskStatus.AWAITING_CONFIRM, TaskStatus.EXECUTING)


def test_orchestrator_requests_plan_review_confirmation(monkeypatch, tmp_path: Path):
    file_path = _make_file(tmp_path, "sample.docx")
    orchestrator = Orchestrator()
    task = orchestrator.start(file_path, "请按模板写入内容")

    def fake_analyze(file_info: FileInfo) -> FileAnalysis:
        return FileAnalysis(file_info=file_info, text_content="existing text")

    def fake_plan(
        task_type: TaskType,
        analysis: FileAnalysis,
        user_input: str,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            task_id=task.task_id,
            intent="写入文档内容",
            actions=[
                Action(
                    tool_name="insert_text_by_anchor",
                    action_type=ActionType.WRITE,
                    description="按锚点写入文档",
                    params={"path": analysis.file_info.file_path},
                    requires_confirmation=True,
                )
            ],
            expected_output="生成更新后的 Word 文件",
        )

    monkeypatch.setattr("packages.agent_core.orchestrator.analyze_file", fake_analyze)
    monkeypatch.setattr(
        "packages.agent_core.orchestrator.classify_task",
        lambda user_input, file_type: TaskType.WORD_WRITE,
    )
    monkeypatch.setattr("packages.agent_core.orchestrator.generate_plan", fake_plan)

    plan = orchestrator.analyze_and_plan(task.task_id)
    current_task = orchestrator.get_task(task.task_id)

    assert plan.needs_confirmation() is True
    assert current_task is not None
    assert current_task.status == TaskStatus.AWAITING_CONFIRM
    assert current_task.confirmation_request is not None
    assert current_task.confirmation_request.kind == ConfirmationKind.PLAN_REVIEW
    assert current_task.confirmation_request.stage == ConfirmationStage.PLANNED

    orchestrator.confirm(task.task_id)
    resumed_task = orchestrator.get_task(task.task_id)

    assert resumed_task is not None
    assert resumed_task.status == TaskStatus.EXECUTING
    assert resumed_task.confirmation_request is None


def test_orchestrator_requests_ambiguity_confirmation_during_analysis(
    monkeypatch,
    tmp_path: Path,
):
    file_path = _make_file(tmp_path, "form.pdf")
    orchestrator = Orchestrator()
    task = orchestrator.start(file_path, "帮我处理这个表单")
    calls = {"count": 0}

    def fake_analyze(file_info: FileInfo) -> FileAnalysis:
        calls["count"] += 1
        if calls["count"] == 1:
            return FileAnalysis(
                file_info=file_info,
                text_content="ambiguous pdf",
                ambiguities=["检测到多个候选表单版本，需要用户选择。"],
            )
        return FileAnalysis(file_info=file_info, text_content="resolved pdf")

    def fake_plan(
        task_type: TaskType,
        analysis: FileAnalysis,
        user_input: str,
    ) -> ExecutionPlan:
        assert user_input == "请按 A 版表单处理"
        return ExecutionPlan(
            task_id=task.task_id,
            intent="重新规划后的 PDF 处理",
            actions=[
                Action(
                    tool_name="read_pdf_text",
                    action_type=ActionType.READ,
                    description="读取 PDF 文本",
                    params={"path": analysis.file_info.file_path},
                    requires_confirmation=False,
                )
            ],
            expected_output="提取并展示 PDF 内容",
        )

    monkeypatch.setattr("packages.agent_core.orchestrator.analyze_file", fake_analyze)
    monkeypatch.setattr(
        "packages.agent_core.orchestrator.classify_task",
        lambda user_input, file_type: TaskType.PDF_READ,
    )
    monkeypatch.setattr("packages.agent_core.orchestrator.generate_plan", fake_plan)

    plan = orchestrator.analyze_and_plan(task.task_id)
    current_task = orchestrator.get_task(task.task_id)

    assert plan.intent == "等待人工消解歧义"
    assert current_task is not None
    assert current_task.status == TaskStatus.AWAITING_CONFIRM
    assert current_task.confirmation_request is not None
    assert (
        current_task.confirmation_request.kind
        == ConfirmationKind.AMBIGUITY_RESOLUTION
    )
    assert current_task.confirmation_request.stage == ConfirmationStage.ANALYZING

    orchestrator.confirm(task.task_id)
    resumed_task = orchestrator.get_task(task.task_id)

    assert resumed_task is not None
    assert resumed_task.status == TaskStatus.ANALYZING
    assert resumed_task.confirmation_request is None

    resumed_plan = orchestrator.resume(task.task_id, user_input="请按 A 版表单处理")
    resumed_task = orchestrator.get_task(task.task_id)

    assert resumed_task is not None
    assert resumed_task.user_input == "请按 A 版表单处理"
    assert resumed_task.status == TaskStatus.PLANNED
    assert resumed_plan.intent == "重新规划后的 PDF 处理"


def test_risky_action_request_builder_marks_executing_stage():
    request = ConfirmationGate.build_risky_action_request(
        action_id="write-1",
        tool_name="replace_docx_content",
        description="覆盖原文档内容",
        details={"target": "report.docx"},
    )

    assert request.kind == ConfirmationKind.RISKY_ACTION
    assert request.stage == ConfirmationStage.EXECUTING
    assert request.resume_from == "action:write-1"
    assert request.details["target"] == "report.docx"
