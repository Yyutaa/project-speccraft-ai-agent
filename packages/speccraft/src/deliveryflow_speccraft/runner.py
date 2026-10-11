"""Synchronous in-memory happy path used by the Phase 01 teaching scaffold."""

from threading import Lock
from uuid import uuid4

from deliveryflow_contracts.runs import (
    Approval,
    AvailableCommand,
    CreateRunRequest,
    DeliverySpec,
    DraftArtifact,
    RunResponse,
    RunStatus,
)


class RunNotFound(Exception):
    """Raised when a Run identifier is not present in this process."""


class InvalidRunTransition(Exception):
    """Raised when a command is not available in the current Run state."""


class RevisionConflict(Exception):
    """Raised when an approval refers to a different draft revision."""


class FakeProvider:
    """Creates deterministic draft text without calling an external model."""

    def create_prd(self, requirement: str) -> DraftArtifact:
        return DraftArtifact(
            revision=1,
            content=(
                "# 产品需求文档\n\n"
                f"## 需求\n{requirement}\n\n"
                "## 验收标准\n"
                "- 结果符合上述需求。\n"
                "- 用户可以确认该产品规格。\n"
            ),
        )

    def create_td(self, approved_prd: DraftArtifact) -> DraftArtifact:
        return DraftArtifact(
            revision=1,
            content=(
                "# 技术方案\n\n"
                "## 已批准 PRD\n"
                f"{approved_prd.content}\n"
                "## 实现策略\n"
                "按 PRD 中的需求和验收标准实现，并保持技术方案不回写 PRD。\n"
            ),
        )


class InMemoryRunner:
    """Owns Run state for one API process; restarting the process clears it."""

    def __init__(self) -> None:
        self._provider = FakeProvider()
        self._runs: dict[str, RunResponse] = {}
        self._lock = Lock()

    def create_run(self, request: CreateRunRequest) -> RunResponse:
        prd = self._provider.create_prd(request.requirement)
        run_id = str(uuid4())
        run = RunResponse(
            run_id=run_id,
            requirement=request.requirement,
            status=RunStatus.PRD_AWAITING_APPROVAL,
            prd_draft=prd,
            available_commands=(AvailableCommand.APPROVE_PRD,),
        )
        with self._lock:
            self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> RunResponse:
        with self._lock:
            return self._require_run(run_id)

    def approve_prd(self, run_id: str, revision: int) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            if run.status is not RunStatus.PRD_AWAITING_APPROVAL:
                raise InvalidRunTransition("PRD is not awaiting approval")
            if revision != run.prd_draft.revision:
                raise RevisionConflict("PRD revision does not match the current draft")

            td = self._provider.create_td(run.prd_draft)
            updated = run.model_copy(
                update={
                    "status": RunStatus.TD_AWAITING_APPROVAL,
                    "prd_approval": Approval(revision=revision),
                    "td_draft": td,
                    "available_commands": (AvailableCommand.APPROVE_TD,),
                }
            )
            self._runs[run_id] = updated
            return updated

    def approve_td(self, run_id: str, revision: int) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            if run.status is not RunStatus.TD_AWAITING_APPROVAL:
                raise InvalidRunTransition("TD is not awaiting approval")
            if run.td_draft is None:
                raise InvalidRunTransition("TD draft is missing")
            if revision != run.td_draft.revision:
                raise RevisionConflict("TD revision does not match the current draft")
            if run.prd_approval is None:
                raise InvalidRunTransition("PRD has not been approved")

            delivery_spec = DeliverySpec(
                run_id=run.run_id,
                prd_revision=run.prd_draft.revision,
                td_revision=run.td_draft.revision,
                prd_content=run.prd_draft.content,
                td_content=run.td_draft.content,
            )
            updated = run.model_copy(
                update={
                    "status": RunStatus.COMPLETED,
                    "td_approval": Approval(revision=revision),
                    "delivery_spec": delivery_spec,
                    "available_commands": (),
                }
            )
            self._runs[run_id] = updated
            return updated

    def _require_run(self, run_id: str) -> RunResponse:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise RunNotFound(run_id) from error
