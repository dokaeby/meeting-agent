import pytest

from meeting_agent.modules.summary import parse_transcript, validate_summary


def test_vtt_and_evidence():
    segments = parse_transcript(
        "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n김팀장: 다음 출시를 준비합니다."
    )
    assert len(segments) == 1
    assert segments[0]["text"].startswith("김팀장")
    body = {"title": "회의", "overview": {"text": "출시 준비", "evidence_ids": ["s1"]}}
    assert validate_summary(body, segments)["title"] == "회의"
    body["overview"]["evidence_ids"] = ["invented"]
    with pytest.raises(ValueError, match="evidence"):
        validate_summary(body, segments)


def test_empty_transcript_rejected():
    with pytest.raises(ValueError):
        parse_transcript("  ")
