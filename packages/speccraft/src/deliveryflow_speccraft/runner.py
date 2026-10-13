"""Synchronous in-memory Run orchestration for the teaching scaffold."""

from hashlib import sha256
from pathlib import Path
from threading import Lock
from uuid import uuid4

from deliveryflow_contracts.facts import (
    ClarificationBatch,
    ClarificationOption,
    ClarificationProposal,
    CompletenessResult,
    DecisionEvidence,
    FactDimension,
    FactKind,
    FactLedger,
    GapSignal,
    RequirementFact,
    SourceEvidence,
    SubmitClarificationRequest,
)
from deliveryflow_contracts.prd import (
    PrdApprovalReceipt,
    PrdApprovalRequest,
    PrdBlueprint,
    PrdReadiness,
    PrdRevision,
    PrdRevisionRequest,
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

from deliveryflow_speccraft.completeness import CompletenessAnalyzer
from deliveryflow_speccraft.prd import (
    build_prd_blueprint,
    check_prd_readiness,
    replace_prd_section,
)
from deliveryflow_speccraft.prd_authoring import (
    FakePrdAuthor,
    PrdAuthor,
    load_prd_authoring_pack,
)
from deliveryflow_speccraft.repository_context import RepositoryHarness


class RunNotFound(Exception):
    """Raised when a Run identifier is not present in this process."""


class InvalidRunTransition(Exception):
    """Raised when a command is not available in the current Run state."""


class RevisionConflict(Exception):
    """Raised when an approval refers to a different draft revision."""


class InvalidClarification(Exception):
    """Raised when an answer does not cover the current blocking questions."""


class DuplicateCommand(Exception):
    """Raised when an in-memory command identifier is submitted more than once."""


class ContentHashConflict(Exception):
    """Raised when a command names a different PRD content hash."""


class PrdNotReady(Exception):
    """Raised when structural PRD checks have unresolved issues."""


class InvalidPrdRevision(Exception):
    """Raised when a requested PRD edit escapes its target section."""


class FakeProvider:
    """Retains the deterministic TD demo and clarification proposals."""

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

    def propose_clarifications(
        self, gaps: tuple[GapSignal, ...]
    ) -> tuple[ClarificationProposal, ...]:
        labels = {
            FactDimension.ROLE: "主要使用角色",
            FactDimension.WORKFLOW: "主要业务流程",
            FactDimension.PERMISSION: "权限规则",
            FactDimension.FAILURE: "失败时的处理方式",
            FactDimension.ACCEPTANCE: "验收标准",
        }
        choices = {
            FactDimension.ROLE: (("administrator", "管理员"), ("operator", "操作人员")),
            FactDimension.WORKFLOW: (("single_step", "单步骤流程"), ("multi_step", "多步骤流程")),
            FactDimension.PERMISSION: (
                ("role_based", "按角色限制"),
                ("all_users", "所有用户均可操作"),
            ),
            FactDimension.FAILURE: (
                ("stop_and_notify", "停止并提示错误"),
                ("allow_retry", "允许重试"),
            ),
            FactDimension.ACCEPTANCE: (
                ("testable", "使用可验证的验收条件"),
                ("user_review", "由用户确认结果"),
            ),
        }
        return tuple(
            ClarificationProposal(
                question_id=gap.gap_id,
                gap_id=gap.gap_id,
                question=f"请明确{labels[gap.dimension]}。",
                options=tuple(
                    ClarificationOption(option_id=option_id, label=label)
                    for option_id, label in choices[gap.dimension]
                ),
                recommended_option_id=choices[gap.dimension][0][0],
                recommendation_reason="确定性示例建议，需由用户显式选择后才成为决定。",
            )
            for gap in gaps
        )


class InMemoryRunner:
    """Owns Run state for one API process; restarting the process clears it."""

    def __init__(
        self,
        harness: RepositoryHarness,
        prd_authoring_directory: Path,
        prd_author: PrdAuthor | None = None,
    ) -> None:
        self._provider = FakeProvider()
        self._prd_author = prd_author or FakePrdAuthor()
        self._prd_pack = load_prd_authoring_pack(prd_authoring_directory)
        self._analyzer = CompletenessAnalyzer()
        self._harness = harness
        self._runs: dict[str, RunResponse] = {}
        self._used_command_ids: dict[str, set[str]] = {}
        self._lock = Lock()

    def create_run(self, request: CreateRunRequest) -> RunResponse:
        context = self._harness.build(request)
        requirement = context.requirement.content.strip()
        ledger = FactLedger(
            revision=1,
            facts=(RequirementFact(
                fact_id="source-requirement",
                kind=FactKind.FACT,
                dimension=None,
                claim=requirement,
                source=SourceEvidence(
                    sha256=context.requirement.sha256,
                    excerpt=context.requirement.content,
                ),
            ),),
        )
        completeness = self._analyzer.analyze(ledger)
        awaiting = not completeness.is_complete
        batch = (
            self._make_batch(ledger, completeness, revision=1)
            if awaiting
            else None
        )
        blueprint: PrdBlueprint | None = None
        prd: PrdRevision | None = None
        readiness: PrdReadiness | None = None
        if not awaiting:
            blueprint, prd, readiness = self._create_prd(ledger)
        run_id = str(uuid4())
        run = RunResponse(
            run_id=run_id,
            requirement=requirement,
            status=(
                RunStatus.AWAITING_CLARIFICATION
                if awaiting
                else RunStatus.PRD_AWAITING_APPROVAL
            ),
            prd_draft=prd,
            prd_blueprint=blueprint,
            prd_readiness=readiness,
            prd_revisions=(prd,) if prd is not None else (),
            available_commands=(
                (AvailableCommand.SUBMIT_CLARIFICATION,)
                if awaiting
                else self._prd_commands(readiness)
            ),
            source_snapshot=context.requirement,
            repository_binding=context.binding,
            harness_context=context.context,
            ledger=ledger,
            completeness=completeness,
            clarification_batch=batch,
        )
        with self._lock:
            self._runs[run_id] = run
            self._used_command_ids[run_id] = set()
        return run

    def submit_clarification(
        self, run_id: str, request: SubmitClarificationRequest
    ) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            used_command_ids = self._used_command_ids[run_id]
            if request.command_id in used_command_ids:
                raise DuplicateCommand(request.command_id)
            if run.status is not RunStatus.AWAITING_CLARIFICATION:
                raise InvalidRunTransition("Run is not awaiting clarification")
            if request.expected_revision != run.ledger.revision:
                raise RevisionConflict("Fact Ledger revision does not match the current Run")
            batch = run.clarification_batch
            if batch is None:
                raise InvalidClarification("clarification batch is missing")

            proposals = {proposal.question_id: proposal for proposal in batch.proposals}
            blocking_question_ids = {
                proposal.question_id
                for proposal in batch.proposals
                if proposal.gap_id in batch.blocking_gap_ids
            }
            answers_by_id = {answer.question_id: answer for answer in request.answers}
            if set(answers_by_id) != blocking_question_ids:
                raise InvalidClarification(
                    "answers must cover every blocking question exactly once"
                )

            gaps = {gap.gap_id: gap for gap in run.completeness.gaps}
            decisions: list[RequirementFact] = []
            for answer in request.answers:
                proposal = proposals.get(answer.question_id)
                if proposal is None:
                    raise InvalidClarification("answer refers to an unknown question")
                gap = gaps.get(proposal.gap_id)
                if gap is None:
                    raise InvalidClarification("question no longer refers to a current gap")
                if answer.selected_option_id is not None:
                    option = next(
                        (
                            option
                            for option in proposal.options
                            if option.option_id == answer.selected_option_id
                        ),
                        None,
                    )
                    if option is None:
                        raise InvalidClarification("selected option is not part of the question")
                    claim = option.label
                else:
                    claim = (answer.custom_answer or "").strip()
                decisions.append(
                    RequirementFact(
                        fact_id=f"decision-{batch.revision}-{answer.question_id}",
                        kind=FactKind.DECISION,
                        dimension=gap.dimension,
                        claim=claim,
                        decision_evidence=DecisionEvidence(
                            batch_id=batch.batch_id,
                            question_id=answer.question_id,
                            command_id=request.command_id,
                            expected_revision=request.expected_revision,
                            answer=claim,
                        ),
                    )
                )

            ledger = FactLedger(
                revision=run.ledger.revision + 1,
                facts=run.ledger.facts + tuple(decisions),
            )
            completeness = self._analyzer.analyze(ledger)
            if completeness.is_complete:
                blueprint, prd, readiness = self._create_prd(ledger)
                updated = self._validated_update(
                    run, {
                        "ledger": ledger, "completeness": completeness,
                        "status": RunStatus.PRD_AWAITING_APPROVAL,
                        "prd_blueprint": blueprint, "prd_draft": prd,
                        "prd_revisions": (prd,), "prd_readiness": readiness,
                        "available_commands": self._prd_commands(readiness),
                    },
                )
            else:
                next_batch = self._make_batch(
                    ledger,
                    completeness,
                    revision=batch.revision + 1,
                )
                updated = self._validated_update(
                    run, {
                        "ledger": ledger,
                        "completeness": completeness,
                        "clarification_batch": next_batch,
                    },
                )

            self._runs[run_id] = updated
            used_command_ids.add(request.command_id)
            return updated

    def get_run(self, run_id: str) -> RunResponse:
        with self._lock:
            return self._require_run(run_id)

    def revise_prd(self, run_id: str, request: PrdRevisionRequest) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            if run.status is not RunStatus.PRD_AWAITING_APPROVAL or run.prd_draft is None:
                raise InvalidRunTransition("PRD is frozen or has not been created")
            if request.expected_revision != run.prd_draft.revision:
                raise RevisionConflict("PRD revision does not match the current draft")
            if request.expected_content_hash != run.prd_draft.content_hash:
                raise ContentHashConflict("PRD hash does not match the current draft")
            try:
                content = replace_prd_section(
                    run.prd_draft.content, request.section_id, request.replacement_body
                )
            except ValueError as error:
                raise InvalidPrdRevision(str(error)) from error
            revision = PrdRevision(
                revision=run.prd_draft.revision + 1,
                content=content,
                content_hash=sha256(content.encode("utf-8")).hexdigest(),
                changed_section_id=request.section_id,
                feedback=request.feedback.strip(),
            )
            readiness = check_prd_readiness(revision)
            updated = self._validated_update(run, {
                "prd_draft": revision,
                "prd_revisions": run.prd_revisions + (revision,),
                "prd_readiness": readiness,
                "available_commands": self._prd_commands(readiness),
            })
            self._runs[run_id] = updated
            return updated

    def approve_prd(self, run_id: str, request: PrdApprovalRequest) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            if run.status is not RunStatus.PRD_AWAITING_APPROVAL:
                raise InvalidRunTransition("PRD is not awaiting approval")
            if run.prd_draft is None:
                raise InvalidRunTransition("PRD draft is missing")
            if request.revision != run.prd_draft.revision:
                raise RevisionConflict("PRD revision does not match the current draft")
            if request.content_hash != run.prd_draft.content_hash:
                raise ContentHashConflict("PRD hash does not match the current draft")
            if run.prd_readiness is None or not run.prd_readiness.ready:
                raise PrdNotReady("PRD has unresolved structural issues")

            td = self._provider.create_td(DraftArtifact(
                revision=run.prd_draft.revision,
                content=run.prd_draft.content,
            ))
            updated = self._validated_update(
                run, {
                    "status": RunStatus.TD_AWAITING_APPROVAL,
                    "prd_approval": PrdApprovalReceipt(**request.model_dump()),
                    "td_draft": td,
                    "available_commands": (AvailableCommand.APPROVE_TD,),
                },
            )
            self._runs[run_id] = updated
            return updated

    def approve_td(self, run_id: str, revision: int) -> RunResponse:
        with self._lock:
            run = self._require_run(run_id)
            if run.status is not RunStatus.TD_AWAITING_APPROVAL:
                raise InvalidRunTransition("TD is not awaiting approval")
            if run.prd_draft is None:
                raise InvalidRunTransition("PRD draft is missing")
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
            updated = self._validated_update(
                run, {
                    "status": RunStatus.COMPLETED,
                    "td_approval": Approval(revision=revision),
                    "delivery_spec": delivery_spec,
                    "available_commands": (),
                },
            )
            self._runs[run_id] = updated
            return updated

    def _require_run(self, run_id: str) -> RunResponse:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise RunNotFound(run_id) from error

    def _create_prd(
        self, ledger: FactLedger
    ) -> tuple[PrdBlueprint, PrdRevision, PrdReadiness]:
        blueprint = build_prd_blueprint(ledger)
        content = self._prd_author.author(
            blueprint,
            {fact.fact_id: fact.claim for fact in ledger.authoritative_facts},
            self._prd_pack,
        )
        revision = PrdRevision(
            revision=1,
            content=content,
            content_hash=sha256(content.encode("utf-8")).hexdigest(),
        )
        return blueprint, revision, check_prd_readiness(revision)

    @staticmethod
    def _prd_commands(readiness: PrdReadiness | None) -> tuple[AvailableCommand, ...]:
        return (
            (AvailableCommand.REVISE_PRD, AvailableCommand.APPROVE_PRD)
            if readiness is not None and readiness.ready
            else (AvailableCommand.REVISE_PRD,)
        )

    @staticmethod
    def _validated_update(run: RunResponse, update: dict[str, object]) -> RunResponse:
        return RunResponse.model_validate(run.model_copy(update=update).model_dump())

    def _make_batch(
        self,
        ledger: FactLedger,
        completeness: CompletenessResult,
        revision: int,
    ) -> ClarificationBatch:
        proposals = self._provider.propose_clarifications(completeness.gaps)
        gaps = tuple(gap.gap_id for gap in completeness.gaps)
        blocking = tuple(gap.gap_id for gap in completeness.gaps if gap.blocking)
        return ClarificationBatch(
            batch_id=str(uuid4()),
            revision=revision,
            ledger_revision=ledger.revision,
            gap_ids=gaps,
            blocking_gap_ids=blocking,
            proposals=proposals,
        )
