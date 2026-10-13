from hashlib import sha256

from deliveryflow_contracts.facts import (
    DecisionEvidence,
    FactDimension,
    FactKind,
    FactLedger,
    RequirementFact,
    SourceEvidence,
)
from deliveryflow_contracts.prd import PrdSectionId
from deliveryflow_speccraft.prd import build_prd_blueprint


def sample_ledger() -> FactLedger:
    source_hash = sha256("原始需求".encode()).hexdigest()
    source = SourceEvidence(sha256=source_hash, excerpt="原始需求")
    facts = [
        RequirementFact(
            fact_id="source-general", kind=FactKind.FACT,
            dimension=None, claim="导出时显示进度", source=source,
        ),
        RequirementFact(
            fact_id="source-role", kind=FactKind.FACT,
            dimension=FactDimension.ROLE, claim="所有人", source=source,
        ),
    ]
    for dimension, claim in (
        (FactDimension.ROLE, "管理员"),
        (FactDimension.WORKFLOW, "选择文件后导出"),
        (FactDimension.PERMISSION, "仅管理员可以导出"),
        (FactDimension.FAILURE, "失败时提示并允许重试"),
        (FactDimension.ACCEPTANCE, "完成后可下载文件"),
    ):
        facts.append(RequirementFact(
            fact_id=f"decision-{dimension.value}", kind=FactKind.DECISION,
            dimension=dimension, claim=claim,
            decision_evidence=DecisionEvidence(
                batch_id="batch-1", question_id=f"question-{dimension.value}",
                command_id="command-1", expected_revision=1, answer=claim,
            ),
        ))
    return FactLedger(revision=2, facts=tuple(facts))


def test_blueprint_references_every_authoritative_fact_and_excludes_overridden_source() -> None:
    ledger = sample_ledger()

    blueprint = build_prd_blueprint(ledger)

    assert tuple(fact.fact_id for fact in ledger.authoritative_facts) == (
        "source-general", "decision-role", "decision-workflow",
        "decision-permission", "decision-failure", "decision-acceptance",
    )
    assert blueprint.authoritative_fact_ids == tuple(
        fact.fact_id for fact in ledger.authoritative_facts
    )
    assert set(blueprint.sections[1].fact_ids) == {"source-general"}
    assert blueprint.sections[3].section_id is PrdSectionId.ACTORS
    assert blueprint.sections[3].fact_ids == ("decision-role",)
    assert "source-role" not in {
        fact_id for section in blueprint.sections for fact_id in section.fact_ids
    }
