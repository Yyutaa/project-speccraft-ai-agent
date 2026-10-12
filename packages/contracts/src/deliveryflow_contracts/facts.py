"""Contracts for evidence-backed requirement facts and user clarification."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FactKind(StrEnum):
    FACT = "fact"
    DECISION = "decision"


class FactDimension(StrEnum):
    ROLE = "role"
    WORKFLOW = "workflow"
    PERMISSION = "permission"
    FAILURE = "failure"
    ACCEPTANCE = "acceptance"


class SourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    excerpt: str = Field(min_length=1, pattern=r".*\S.*")


class DecisionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    answer: str = Field(min_length=1, pattern=r".*\S.*")
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RequirementFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_id: str = Field(min_length=1)
    kind: FactKind
    dimension: FactDimension | None
    claim: str = Field(min_length=1, pattern=r".*\S.*")
    source: SourceEvidence | None = None
    decision_evidence: DecisionEvidence | None = None

    @model_validator(mode="after")
    def validate_authority_evidence(self) -> "RequirementFact":
        if self.kind is FactKind.FACT:
            if self.source is None or self.decision_evidence is not None:
                raise ValueError(
                    "FACT requires source evidence and cannot contain decision evidence"
                )
        elif (
            self.dimension is None
            or self.decision_evidence is None
            or self.source is not None
        ):
            raise ValueError(
                "DECISION requires a dimension and decision evidence, not source evidence"
            )
        elif self.decision_evidence.answer != self.claim:
            raise ValueError("claim must match decision evidence answer")
        return self


class FactLedger(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)
    facts: tuple[RequirementFact, ...]

    @model_validator(mode="after")
    def require_unique_fact_ids(self) -> "FactLedger":
        ids = [fact.fact_id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("fact IDs must be unique")
        return self

    @property
    def authoritative_view(self) -> tuple[str, ...]:
        decisions = {
            fact.dimension: fact.fact_id
            for fact in self.facts
            if fact.kind is FactKind.DECISION
        }
        return tuple(
            fact.claim
            for fact in self.facts
            if (
                fact.kind is FactKind.DECISION
                and decisions.get(fact.dimension) == fact.fact_id
            )
            or (
                fact.kind is FactKind.FACT
                and (fact.dimension is None or fact.dimension not in decisions)
            )
        )


class GapSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gap_id: str = Field(min_length=1)
    dimension: FactDimension
    blocking: bool
    reason: str = Field(min_length=1)
    ledger_revision: int = Field(ge=1)


class CompletenessResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ledger_revision: int = Field(ge=1)
    gaps: tuple[GapSignal, ...]

    @model_validator(mode="after")
    def validate_gap_revisions(self) -> "CompletenessResult":
        if any(gap.ledger_revision != self.ledger_revision for gap in self.gaps):
            raise ValueError("completeness gaps must match the ledger revision")
        gap_ids = [gap.gap_id for gap in self.gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("gap IDs must be unique")
        return self

    @property
    def is_complete(self) -> bool:
        return not any(gap.blocking for gap in self.gaps)


class ClarificationOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1, pattern=r".*\S.*")


class ClarificationProposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str = Field(min_length=1)
    gap_id: str = Field(min_length=1)
    question: str = Field(min_length=1, pattern=r".*\S.*")
    options: tuple[ClarificationOption, ...] = Field(min_length=1)
    recommended_option_id: str | None = None
    recommendation_reason: str | None = Field(default=None, pattern=r".*\S.*")

    @model_validator(mode="after")
    def validate_recommendation(self) -> "ClarificationProposal":
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("clarification option IDs must be unique")
        if self.recommended_option_id is not None:
            if self.recommended_option_id not in option_ids or not self.recommendation_reason:
                raise ValueError("recommended option must exist and include a reason")
        elif self.recommendation_reason is not None:
            raise ValueError("recommendation reason requires a recommended option")
        return self


class ClarificationBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    ledger_revision: int = Field(ge=1)
    gap_ids: tuple[str, ...]
    blocking_gap_ids: tuple[str, ...]
    proposals: tuple[ClarificationProposal, ...]

    @model_validator(mode="after")
    def validate_blocking_gap_coverage(self) -> "ClarificationBatch":
        proposal_ids = [proposal.question_id for proposal in self.proposals]
        proposal_gap_ids = [proposal.gap_id for proposal in self.proposals]
        if len(proposal_ids) != len(set(proposal_ids)):
            raise ValueError("clarification question IDs must be unique")
        if len(proposal_gap_ids) != len(set(proposal_gap_ids)):
            raise ValueError("each gap must have one clarification proposal")
        if len(self.gap_ids) != len(set(self.gap_ids)):
            raise ValueError("gap IDs in a clarification batch must be unique")
        if not set(self.blocking_gap_ids).issubset(self.gap_ids):
            raise ValueError("blocking gaps must belong to the completeness result")
        if not set(proposal_gap_ids).issubset(self.gap_ids):
            raise ValueError("clarification proposals must refer to a known gap")
        if not set(self.blocking_gap_ids).issubset(proposal_gap_ids):
            raise ValueError("clarification batch must cover every blocking gap")
        return self


class ClarificationAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_id: str = Field(min_length=1)
    selected_option_id: str | None = None
    custom_answer: str | None = None

    @model_validator(mode="after")
    def require_one_explicit_answer(self) -> "ClarificationAnswer":
        has_option = self.selected_option_id is not None and bool(self.selected_option_id.strip())
        has_custom = self.custom_answer is not None and bool(self.custom_answer.strip())
        if has_option == has_custom:
            raise ValueError("provide exactly one nonblank option or custom answer")
        return self


class SubmitClarificationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_revision: int = Field(ge=1)
    command_id: str = Field(min_length=1)
    answers: tuple[ClarificationAnswer, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_questions(self) -> "SubmitClarificationRequest":
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("each clarification question can be answered once")
        return self
