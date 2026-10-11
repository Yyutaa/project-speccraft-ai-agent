import pytest
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


def test_create_run_request_trims_requirement_and_rejects_blank_text() -> None:
    request = CreateRunRequest(requirement="  导出大文件时显示进度。  ")

    assert request.requirement == "导出大文件时显示进度。"
    with pytest.raises(ValidationError):
        CreateRunRequest(requirement=" \n ")


def test_prd_waiting_run_has_only_the_prd_approval_command() -> None:
    run = RunResponse(
        run_id="run-1",
        requirement="导出大文件时显示进度。",
        status=RunStatus.PRD_AWAITING_APPROVAL,
        prd_draft=DraftArtifact(revision=1, content="# PRD"),
        available_commands=(AvailableCommand.APPROVE_PRD,),
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
    )

    assert run.model_dump(mode="json")["status"] == "completed"
    assert run.delivery_spec is not None
    assert run.prd_approval is not None
    assert run.delivery_spec.prd_revision == run.prd_approval.revision
