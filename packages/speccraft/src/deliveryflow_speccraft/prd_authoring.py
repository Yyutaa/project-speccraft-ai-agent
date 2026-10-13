"""Read the PRD authoring pack and provide a deterministic author for V0."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from deliveryflow_contracts.prd import SECTION_TITLES, PrdBlueprint, PrdSectionId


@dataclass(frozen=True)
class PrdAuthoringPack:
    template: str
    guide: str
    self_check: str


def load_prd_authoring_pack(directory: Path) -> PrdAuthoringPack:
    pack = PrdAuthoringPack(
        template=(directory / "template.md").read_text(encoding="utf-8"),
        guide=(directory / "authoring-guide.md").read_text(encoding="utf-8"),
        self_check=(directory / "self-check.md").read_text(encoding="utf-8"),
    )
    headings = tuple(
        line.removeprefix("## ")
        for line in pack.template.splitlines()
        if line.startswith("## ")
    )
    if headings != tuple(SECTION_TITLES.values()):
        raise ValueError("PRD template chapters do not match the public Blueprint")
    return pack


class PrdAuthor(Protocol):
    def author(
        self,
        blueprint: PrdBlueprint,
        authoritative_claims: dict[str, str],
        pack: PrdAuthoringPack,
    ) -> str: ...


class FakePrdAuthor:
    """Fills template sections with cited claims; it does not judge content quality."""

    def author(
        self,
        blueprint: PrdBlueprint,
        authoritative_claims: dict[str, str],
        pack: PrdAuthoringPack,
    ) -> str:
        if set(authoritative_claims) != set(blueprint.authoritative_fact_ids):
            raise ValueError("author input must exactly match authoritative fact references")
        sections: dict[PrdSectionId, str] = {}
        for section in blueprint.sections:
            if section.section_id is PrdSectionId.DOCUMENT_INFO:
                body = "文档依据：已确认的需求事实与用户决定。"
            elif not section.applicable:
                body = f"不适用：{section.applicability_reason}"
            elif section.fact_ids:
                body = "\n".join(
                    "- " + authoritative_claims[fact_id].strip().replace("\n", "\n  ")
                    for fact_id in section.fact_ids
                )
            else:
                body = "本节没有额外的已确认事实。"
            sections[section.section_id] = body

        replacements = {
            "title": "需求规格",
            "document_meta": sections[PrdSectionId.DOCUMENT_INFO],
            "background_objectives": sections[PrdSectionId.BACKGROUND],
            "scope": sections[PrdSectionId.SCOPE],
            "actors": sections[PrdSectionId.ACTORS],
            "journeys": sections[PrdSectionId.JOURNEYS],
            "rules": sections[PrdSectionId.RULES],
            "exceptions": sections[PrdSectionId.EXCEPTIONS],
            "acceptance": sections[PrdSectionId.ACCEPTANCE],
        }
        content = pack.template
        for key, value in replacements.items():
            content = content.replace("{{ " + key + " }}", value)
        if "{{" in content or "}}" in content:
            raise ValueError("PRD template has unresolved placeholders")
        return content
