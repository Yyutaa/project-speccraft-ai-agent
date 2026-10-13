from hashlib import sha256

from deliveryflow_contracts.prd import PrdRevision
from deliveryflow_speccraft.prd import check_prd_readiness

SECTIONS = (
    "文档信息",
    "背景、目标与成功标准",
    "范围与非目标",
    "角色与场景",
    "功能与核心业务流程",
    "业务规则与产品边界",
    "异常体验与产品规则",
    "验收标准",
)


def document(sections: tuple[str, ...] = SECTIONS, body: str = "已确认内容。") -> str:
    return "# 产品需求文档：需求规格\n\n" + "\n\n".join(
        f"## {title}\n{body}" for title in sections
    ) + "\n"


def revision(content: str) -> PrdRevision:
    return PrdRevision(
        revision=1, content=content,
        content_hash=sha256(content.encode("utf-8")).hexdigest(),
    )


def test_complete_document_passes_basic_readiness() -> None:
    result = check_prd_readiness(revision(document()))

    assert result.ready
    assert result.issues == ()


def test_missing_or_out_of_order_section_has_specific_failure_evidence() -> None:
    missing = check_prd_readiness(revision(document(SECTIONS[:-1])))
    reordered = check_prd_readiness(revision(document((SECTIONS[1], SECTIONS[0], *SECTIONS[2:]))))

    assert ("missing_section", "acceptance") in {
        (issue.code, issue.section_id) for issue in missing.issues
    }
    assert "out_of_order" in {issue.code for issue in reordered.issues}


def test_empty_section_and_placeholder_block_approval() -> None:
    empty = document().replace("## 角色与场景\n已确认内容。", "## 角色与场景\n")
    placeholder = document().replace("## 验收标准\n已确认内容。", "## 验收标准\nTODO")

    assert ("empty_section", "actors") in {
        (issue.code, issue.section_id)
        for issue in check_prd_readiness(revision(empty)).issues
    }
    assert ("placeholder", "acceptance") in {
        (issue.code, issue.section_id)
        for issue in check_prd_readiness(revision(placeholder)).issues
    }
