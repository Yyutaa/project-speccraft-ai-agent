import hashlib

import pytest
from deliveryflow_contracts.context import (
    ContextMode,
    HarnessContextSlice,
    RepositoryBinding,
    SourceRef,
    SourceSnapshot,
    SourceType,
)
from deliveryflow_contracts.runs import (
    Approval,
    AvailableCommand,
    CreateRunRequest,
    DeliverySpec,
    DraftArtifact,
    RunResponse,
    RunStatus,
)
from pydantic import ValidationError


def context_fields() -> dict[str, object]:
    return {
        "source_snapshot": SourceSnapshot(
            source=SourceRef(source_type=SourceType.INLINE_REQUIREMENT),
            sha256=hashlib.sha256("需求".encode()).hexdigest(),
            read_status="read",
            content="需求",
        ),
        "repository_binding": RepositoryBinding(
            repository_id="exportflow-sample",
            root_path="/sample",
            context_mode=ContextMode.GUIDE_ONLY,
        ),
        "harness_context": HarnessContextSlice(
            entries=(), sha256=hashlib.sha256(b"[]").hexdigest()
        ),
    }


def test_create_run_request_preserves_raw_requirement_and_rejects_blank_text() -> None:
    request = CreateRunRequest(requirement="  导出大文件时显示进度。  ")

    assert request.requirement == "  导出大文件时显示进度。  "
    with pytest.raises(ValidationError):
        CreateRunRequest(requirement=" \n ")


def test_prd_waiting_run_has_only_the_prd_approval_command() -> None:
    run = RunResponse(
        run_id="run-1",
        requirement="导出大文件时显示进度。",
        status=RunStatus.PRD_AWAITING_APPROVAL,
        prd_draft=DraftArtifact(revision=1, content="# PRD"),
        available_commands=(AvailableCommand.APPROVE_PRD,),
        **context_fields(),
    )

    assert run.td_draft is None
    assert run.prd_approval is None
    assert run.delivery_spec is None


def test_completed_run_requires_both_approvals_and_delivery_spec() -> None:
    with pytest.raises(ValidationError):
        RunResponse(
            run_id="run-1",
            requirement="导出大文件时显示进度。",
            status=RunStatus.COMPLETED,
            prd_draft=DraftArtifact(revision=1, content="# PRD"),
            prd_approval=Approval(revision=1),
            available_commands=(),
            **context_fields(),
        )


def test_completed_run_contains_version_bound_delivery_spec() -> None:
    run = RunResponse(
        run_id="run-1",
        requirement="导出大文件时显示进度。",
        status=RunStatus.COMPLETED,
        prd_draft=DraftArtifact(revision=1, content="# PRD"),
        prd_approval=Approval(revision=1),
        td_draft=DraftArtifact(revision=1, content="# TD"),
        td_approval=Approval(revision=1),
        delivery_spec=DeliverySpec(
            run_id="run-1",
            prd_revision=1,
            td_revision=1,
            prd_content="# PRD",
            td_content="# TD",
        ),
        available_commands=(),
        **context_fields(),
    )

    assert run.model_dump(mode="json")["status"] == "completed"
    assert run.delivery_spec is not None
    assert run.prd_approval is not None
    assert run.delivery_spec.prd_revision == run.prd_approval.revision
