from pathlib import Path

import pytest
from deliveryflow_contracts.runs import (
    AvailableCommand,
    CreateRunRequest,
    RunStatus,
)
from deliveryflow_speccraft.repository_context import RepositoryHarness
from deliveryflow_speccraft.runner import (
    InMemoryRunner,
    InvalidRunTransition,
    RevisionConflict,
)


def make_runner() -> InMemoryRunner:
    root = Path(__file__).parent.parent / "examples/speccraft/repositories/exportflow-sample"
    return InMemoryRunner(RepositoryHarness(root))


def test_run_moves_from_prd_approval_to_td_approval_to_completion() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))

    assert created.status is RunStatus.PRD_AWAITING_APPROVAL
    assert created.available_commands == (AvailableCommand.APPROVE_PRD,)
    assert created.td_draft is None
    assert created.delivery_spec is None

    after_prd = runner.approve_prd(created.run_id, revision=1)
    assert after_prd.status is RunStatus.TD_AWAITING_APPROVAL
    assert after_prd.prd_approval is not None
    assert after_prd.prd_approval.revision == 1
    assert after_prd.td_draft is not None
    assert after_prd.delivery_spec is None

    completed = runner.approve_td(created.run_id, revision=1)
    assert completed.status is RunStatus.COMPLETED
    assert completed.td_approval is not None
    assert completed.delivery_spec is not None
    assert completed.delivery_spec.run_id == created.run_id
    assert completed.delivery_spec.prd_revision == 1
    assert completed.delivery_spec.td_revision == 1


def test_td_cannot_be_approved_before_prd_and_run_stays_unchanged() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))

    with pytest.raises(InvalidRunTransition):
        runner.approve_td(created.run_id, revision=1)

    assert runner.get_run(created.run_id) == created


def test_stale_prd_revision_is_rejected_without_advancing_run() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))

    with pytest.raises(RevisionConflict):
        runner.approve_prd(created.run_id, revision=2)

    assert runner.get_run(created.run_id) == created


def test_stale_td_revision_is_rejected_without_completing_run() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))
    awaiting_td = runner.approve_prd(created.run_id, revision=1)

    with pytest.raises(RevisionConflict):
        runner.approve_td(created.run_id, revision=2)

    assert runner.get_run(created.run_id) == awaiting_td


def test_repeated_prd_approval_is_rejected_without_changing_td_draft() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))
    after_prd = runner.approve_prd(created.run_id, revision=1)

    with pytest.raises(InvalidRunTransition):
        runner.approve_prd(created.run_id, revision=1)

    assert runner.get_run(created.run_id) == after_prd


def test_repeated_td_approval_is_rejected_without_changing_completed_run() -> None:
    runner = make_runner()
    created = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))
    runner.approve_prd(created.run_id, revision=1)
    completed = runner.approve_td(created.run_id, revision=1)

    with pytest.raises(InvalidRunTransition):
        runner.approve_td(created.run_id, revision=1)

    assert runner.get_run(created.run_id) == completed


def test_fake_provider_generates_same_drafts_for_same_requirement() -> None:
    runner = make_runner()

    first = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))
    second = runner.create_run(CreateRunRequest(requirement="导出时显示进度。"))
    first_completed = runner.approve_prd(first.run_id, revision=1)
    second_completed = runner.approve_prd(second.run_id, revision=1)

    assert first.prd_draft.content == second.prd_draft.content
    assert first_completed.td_draft is not None
    assert second_completed.td_draft is not None
    assert first_completed.td_draft.content == second_completed.td_draft.content
