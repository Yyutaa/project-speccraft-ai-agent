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


class RunStatus(StrEnum):
    PRD_AWAITING_APPROVAL = "prd_awaiting_approval"
    TD_AWAITING_APPROVAL = "td_awaiting_approval"
    COMPLETED = "completed"


class AvailableCommand(StrEnum):
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
    prd_draft: DraftArtifact
    prd_approval: Approval | None = None
    td_draft: DraftArtifact | None = None
    td_approval: Approval | None = None
    delivery_spec: DeliverySpec | None = None
    available_commands: tuple[AvailableCommand, ...]
    source_snapshot: SourceSnapshot
    repository_binding: RepositoryBinding
    harness_context: HarnessContextSlice

    @model_validator(mode="after")
    def validate_state_projection(self) -> "RunResponse":
        if self.status is RunStatus.PRD_AWAITING_APPROVAL:
            valid = (
                self.prd_approval is None
                and self.td_draft is None
                and self.td_approval is None
                and self.delivery_spec is None
                and self.available_commands == (AvailableCommand.APPROVE_PRD,)
            )
        elif self.status is RunStatus.TD_AWAITING_APPROVAL:
            valid = (
                self.prd_approval is not None
                and self.prd_approval.revision == self.prd_draft.revision
                and self.td_draft is not None
                and self.td_approval is None
                and self.delivery_spec is None
                and self.available_commands == (AvailableCommand.APPROVE_TD,)
            )
        else:
            valid = (
                self.prd_approval is not None
                and self.prd_approval.revision == self.prd_draft.revision
                and self.td_draft is not None
                and self.td_approval is not None
                and self.td_approval.revision == self.td_draft.revision
                and self.delivery_spec is not None
                and self.available_commands == ()
            )

        if not valid:
            raise ValueError("Run status, approvals, artifacts, and commands are inconsistent")

        if self.delivery_spec is not None and (
            self.delivery_spec.run_id != self.run_id
            or self.delivery_spec.prd_revision != self.prd_draft.revision
            or self.delivery_spec.prd_content != self.prd_draft.content
            or self.td_draft is None
            or self.delivery_spec.td_revision != self.td_draft.revision
            or self.delivery_spec.td_content != self.td_draft.content
        ):
            raise ValueError("DeliverySpec must reference the approved Run artifacts")

        return self
