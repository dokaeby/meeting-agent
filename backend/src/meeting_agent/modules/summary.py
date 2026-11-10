import re

from ..schemas import Summary


def parse_transcript(value: str) -> list[dict]:
    value = value.lstrip("\ufeff").strip()
    lines = []
    for block in re.split(r"\n\s*\n", value.replace("\r\n", "\n")):
        text = " ".join(
            line.strip()
            for line in block.splitlines()
            if line.strip()
            and not line.strip().isdigit()
            and "-->" not in line
            and line.strip() != "WEBVTT"
        )
        if text:
            for offset in range(0, len(text), 4000):
                lines.append({"id": f"s{len(lines) + 1}", "text": text[offset : offset + 4000]})
    if not lines:
        raise ValueError("empty transcript")
    return lines


def validate_summary(value: dict, segments: list[dict]) -> dict:
    result = Summary.model_validate(value)
    known = {s["id"] for s in segments}
    for item in [result.overview, *result.discussions, *result.decisions, *result.actions]:
        if not set(item.evidence_ids).issubset(known):
            raise ValueError("unknown evidence ID")
    return result.model_dump(mode="json")


def match_assignees(content: dict, members: list[tuple]) -> dict:
    warnings = list(content["warnings"])
    valid = {user.id for _, user in members}
    for item in content["actions"]:
        # LLM-supplied IDs never establish identity.
        item["assignee_id"] = None
        name = item.get("assignee_name")
        matches = [
            user.id for member, user in members if name and name in [user.email, *member.aliases]
        ]
        if len(matches) == 1 and matches[0] in valid:
            item["assignee_id"] = matches[0]
        else:
            warnings.append("담당자 확인 필요")
        if item.get("due_raw") and not item.get("due_at"):
            warnings.append("기한 확인 필요")
    content["warnings"] = list(dict.fromkeys(warnings))
    return content
