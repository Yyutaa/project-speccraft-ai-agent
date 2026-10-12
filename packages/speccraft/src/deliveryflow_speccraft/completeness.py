"""Deterministic completeness checks over the authoritative Fact Ledger."""

from deliveryflow_contracts.facts import (
    CompletenessResult,
    FactDimension,
    FactKind,
    FactLedger,
    GapSignal,
)


class CompletenessAnalyzer:
    """Marks unrepresented or conflicting blocking dimensions as gaps."""

    def analyze(self, ledger: FactLedger) -> CompletenessResult:
        gaps: list[GapSignal] = []
        for dimension in FactDimension:
            facts = [
                fact
                for fact in ledger.facts
                if fact.kind is FactKind.FACT and fact.dimension is dimension
            ]
            decisions = [
                fact
                for fact in ledger.facts
                if fact.kind is FactKind.DECISION and fact.dimension is dimension
            ]
            distinct_claims = {fact.claim.strip().casefold() for fact in facts}
            if decisions or (facts and len(distinct_claims) == 1):
                continue

            reason = (
                f"{dimension.value} 信息存在冲突"
                if facts
                else f"缺少 {dimension.value} 信息"
            )
            gaps.append(
                GapSignal(
                    gap_id=f"gap-{dimension.value}",
                    dimension=dimension,
                    blocking=True,
                    reason=reason,
                    ledger_revision=ledger.revision,
                )
            )
        return CompletenessResult(ledger_revision=ledger.revision, gaps=tuple(gaps))
