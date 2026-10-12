"""Public request and response models for the in-memory Run demonstration."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deliveryflow_contracts.context import (
    ContextMode,
    HarnessContextSlice,
    RepositoryBinding,
    SourceSnapshot,
)
from deliveryflow_contracts.facts import (
    ClarificationBatch,
    CompletenessResult,
    FactKind,
    FactLedger,
)


class RunStatus(StrEnum):
    AWAITING_CLARIFICATION = "awaiting_clarification"
    PRD_AWAITING_APPROVAL = "prd_awaiting_approval"
    TD_AWAITING_APPROVAL = "td_awaiting_approval"
    COMPLETED = "completed"


class AvailableCommand(StrEnum):
    SUBMIT_CLARIFICATION = "submit_clarification"
    APPROVE_PRD = "approve_prd"
    APPROVE_TD = "approve_td"


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requirement: str | None = None
    requirement_path: str | None = Field(default=None, min_length=1)
    context_mode: ContextMode = ContextMode.INDEXED_READONLY

    @model_validator(mode="after")
    def require_one_requirement_source(self) -> "CreateRunRequest":
        has_inline = self.requirement is not None and bool(self.requirement.strip())
        has_file = self.requirement_path is not None and bool(self.requirement_path.strip())
        if has_inline == has_file:
            raise ValueError("provide exactly one nonblank requirement or requirement_path")
        return self


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)


class DraftArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)
    content: str = Field(min_length=1)


class Approval(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliverySpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    prd_revision: int = Field(ge=1)
    td_revision: int = Field(ge=1)
    prd_content: str = Field(min_length=1)
    td_content: str = Field(min_length=1)


class RunResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    requirement: str = Field(min_length=1)
    status: RunStatus
    prd_draft: DraftArtifact | None = None
    prd_approval: Approval | None = None
    td_draft: DraftArtifact | None = None
    td_approval: Approval | None = None
    delivery_spec: DeliverySpec | None = None
    available_commands: tuple[AvailableCommand, ...]
    source_snapshot: SourceSnapshot
    repository_binding: RepositoryBinding
    harness_context: HarnessContextSlice
    ledger: FactLedger
    completeness: CompletenessResult
    clarification_batch: ClarificationBatch | None = None

    @model_validator(mode="after")
    def validate_state_projection(self) -> "RunResponse":
        captured_sources = (
            self.source_snapshot,
            *(entry.snapshot for entry in self.harness_context.entries),
        )
        for fact in self.ledger.facts:
            if fact.kind is FactKind.FACT and fact.source is not None and not any(
                snapshot.sha256 == fact.source.sha256
                and fact.source.excerpt in snapshot.content
                for snapshot in captured_sources
            ):
                raise ValueError("source evidence must match a captured snapshot")

        if self.ledger.revision != self.completeness.ledger_revision:
            raise ValueError("completeness must describe the current Fact Ledger revision")

        if self.status is RunStatus.AWAITING_CLARIFICATION:
            valid = (
                self.prd_draft is None
                and self.prd_approval is None
                and self.td_draft is None
                and self.td_approval is None
                and self.delivery_spec is None
                and not self.completeness.is_complete
                and self.clarification_batch is not None
                and self.clarification_batch.ledger_revision == self.ledger.revision
                and set(self.clarification_batch.blocking_gap_ids)
                == {gap.gap_id for gap in self.completeness.gaps if gap.blocking}
                and self.available_commands == (AvailableCommand.SUBMIT_CLARIFICATION,)
            )
        elif self.status is RunStatus.PRD_AWAITING_APPROVAL:
            valid = (
                self.prd_draft is not None
                and self.prd_approval is None
                and self.td_draft is None
                and self.td_approval is None
                and self.delivery_spec is None
                and self.completeness.is_complete
                and self.available_commands == (AvailableCommand.APPROVE_PRD,)
            )
        elif self.status is RunStatus.TD_AWAITING_APPROVAL:
            valid = (
                self.prd_draft is not None
                and self.prd_approval is not None
                and self.prd_approval.revision == self.prd_draft.revision
                and self.td_draft is not None
                and self.td_approval is None
                and self.delivery_spec is None
                and self.completeness.is_complete
                and self.available_commands == (AvailableCommand.APPROVE_TD,)
            )
        else:
            valid = (
                self.prd_draft is not None
                and self.prd_approval is not None
                and self.prd_approval.revision == self.prd_draft.revision
                and self.td_draft is not None
                and self.td_approval is not None
                and self.td_approval.revision == self.td_draft.revision
                and self.delivery_spec is not None
                and self.completeness.is_complete
                and self.available_commands == ()
            )

        if not valid:
            raise ValueError("Run status, approvals, artifacts, and commands are inconsistent")

        if self.delivery_spec is not None and (
            self.delivery_spec.run_id != self.run_id
            or self.prd_draft is None
            or self.delivery_spec.prd_revision != self.prd_draft.revision
            or self.delivery_spec.prd_content != self.prd_draft.content
            or self.td_draft is None
            or self.delivery_spec.td_revision != self.td_draft.revision
            or self.delivery_spec.td_content != self.td_draft.content
        ):
            raise ValueError("DeliverySpec must reference the approved Run artifacts")

        return self
