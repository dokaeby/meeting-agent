from urllib.parse import quote

import httpx
from sqlalchemy import select

from ..db import owned, transaction
from ..integrations.oauth import access_token
from ..integrations.zoom import download
from ..models import Integration, Job, Meeting, Membership
from ..storage import store
from .runner import assert_claim


class SourceNotReady(ValueError):
    pass


def collect(settings, factory, org, job_id, fence, payload, meeting_id):
    with transaction(factory, org) as db:
        assert_claim(db, org, job_id, fence)
        meeting = owned(db, Meeting, org, id=meeting_id)
        connection = db.scalar(
            select(Integration)
            .where(Integration.org_id == org, Integration.id == payload["integration_id"])
            .with_for_update()
        )
        member = db.get(Membership, (org, connection.user_id)) if connection else None
        if (
            not meeting
            or meeting.deleted
            or not connection
            or not member
            or not member.active
            or connection.status != "connected"
        ):
            owned(db, Job, org, id=job_id).state = "cancelled"
            return
        token = access_token(settings, connection)
    # UUIDs beginning with / or containing // require double encoding in Zoom URLs.
    encoded = quote(payload["external_id"], safe="")
    if payload["external_id"].startswith("/") or "//" in payload["external_id"]:
        encoded = quote(encoded, safe="")
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"https://api.zoom.us/v2/meetings/{encoded}/recordings",
            headers={"Authorization": f"Bearer {token}"},
        )
    response.raise_for_status()
    recordings = [
        f for f in response.json().get("recording_files", []) if f.get("status") == "completed"
    ]
    transcript = next(
        (f for f in recordings if f.get("recording_type") == "audio_transcript"), None
    )
    audio = next((f for f in recordings if f.get("file_type", "").upper() in {"M4A", "MP3"}), None)
    selected = transcript or audio
    if not selected:
        raise SourceNotReady("사용 가능한 Zoom 녹음/녹취가 없습니다")
    from ..models import now

    if (
        not transcript
        and now() - payload.get("received_at", 0) < settings.zoom_transcript_wait_seconds
    ):
        raise SourceNotReady("Zoom 녹취 준비를 기다리는 중입니다")
    # Recheck connection immediately before the download.
    with transaction(factory, org) as db:
        connection = owned(db, Integration, org, id=payload["integration_id"])
        if connection.status != "connected":
            raise ValueError("Zoom 연결이 해제되었습니다")
    content = download(settings, selected["download_url"], token)
    suffix = ".vtt" if transcript else ".m4a"
    key = store(settings, org, meeting_id, content, suffix)
    with transaction(factory, org) as db:
        job = assert_claim(db, org, job_id, fence)
        meeting = owned(db, Meeting, org, id=meeting_id)
        if meeting.deleted:
            job.state = "cancelled"
            return
        dedupe = f"zoom-pipeline:{meeting_id}"
        if not owned(db, Job, org, dedupe_key=dedupe):
            db.add(
                Job(
                    org_id=org,
                    meeting_id=meeting_id,
                    kind="pipeline",
                    dedupe_key=dedupe,
                    input_json={"source_key": key, "generation": meeting.generation},
                )
            )
        meeting.status, job.state = "transcribing", "done"
