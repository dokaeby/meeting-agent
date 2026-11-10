from datetime import datetime, timezone

from sqlalchemy import select

from ..db import owned, transaction
from ..documents import render_pdf
from ..integrations.groq import Groq
from ..models import Approval, Meeting, Membership, Minutes, Organization, Transcript, Usage, User
from ..modules.deliveries import enqueue_deliveries
from ..modules.minutes import approval_hash, latest
from ..modules.summary import match_assignees, parse_transcript
from ..security import snapshot
from ..storage import path_for, store


def process(settings, factory, org, job_id, fence, payload, meeting_id):
    from .runner import assert_claim

    with transaction(factory, org) as db:
        job = assert_claim(db, org, job_id, fence)
        meeting = owned(db, Meeting, org, id=meeting_id)
        company = db.scalar(select(Organization).where(Organization.id == org).with_for_update())
        if not meeting or meeting.deleted or meeting.generation != payload["generation"]:
            job.state = "cancelled"
            return
        title = meeting.title
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        usage = owned(db, Usage, org, period=period)
        if not usage:
            usage = Usage(org_id=org, period=period)
            db.add(usage)
            db.flush()
        if not job.input_json.get("quota_reserved"):
            if usage.meetings >= company.settings.get("monthly_meetings", 100):
                raise ValueError("회사 월 처리 한도 초과")
            usage.meetings += 1
            job.input_json = {**job.input_json, "quota_reserved": True}
        members = list(
            db.execute(
                select(Membership, User)
                .join(User)
                .where(Membership.org_id == org, Membership.active.is_(True))
            )
        )
    path = path_for(settings, payload["source_key"])

    def checkpoint():
        from .runner import CancelledWork

        with transaction(factory, org) as db:
            current_job = assert_claim(db, org, job_id, fence)
            current = owned(db, Meeting, org, id=meeting_id)
            company = db.get(Organization, org)
            if (
                not current
                or current.deleted
                or current.generation != payload["generation"]
                or (settings.environment != "test" and not company.settings.get("ai_consent"))
            ):
                raise CancelledWork("processing cancelled")
            from ..models import now

            current_job.lease_until = now() + 1800

    provider = Groq(settings, checkpoint=checkpoint)
    try:
        if path.suffix.lower() in {".txt", ".srt", ".vtt"}:
            segments, seconds = parse_transcript(path.read_text(encoding="utf-8-sig")), 0
        else:
            segments, seconds = provider.transcribe(path)
        with transaction(factory, org) as db:
            assert_claim(db, org, job_id, fence)
            meeting = owned(db, Meeting, org, id=meeting_id)
            if meeting.deleted:
                return
            meeting.status = "summarizing"
        content, tokens = provider.summarize(segments, title, members)
        content = match_assignees(content, members)
    finally:
        provider.close()
    pdf_key = store(settings, org, meeting_id, render_pdf(content, settings), ".pdf")
    with transaction(factory, org) as db:
        job = assert_claim(db, org, job_id, fence)
        meeting = db.scalar(
            select(Meeting).where(Meeting.org_id == org, Meeting.id == meeting_id).with_for_update()
        )
        if meeting.deleted or meeting.generation != payload["generation"]:
            job.state = "cancelled"
            path_for(settings, pdf_key).unlink(missing_ok=True)
            return
        transcript = owned(db, Transcript, org, meeting_id=meeting_id)
        if not transcript:
            transcript = Transcript(org_id=org, meeting_id=meeting_id)
            db.add(transcript)
        transcript.segments, transcript.source_key = segments, payload["source_key"]
        previous = latest(db, org, meeting_id)
        row = Minutes(
            org_id=org,
            meeting_id=meeting_id,
            version=(previous.version + 1 if previous else 1),
            content=content,
            content_hash=snapshot(content),
            pdf_key=pdf_key,
        )
        db.add(row)
        db.flush()
        meeting.status, job.state = "review_required", "done"
        usage = owned(db, Usage, org, period=period)
        usage.tokens += tokens
        usage.stt_seconds += seconds
        usage.bytes += path.stat().st_size
        company = db.get(Organization, org)
        actor = db.get(Membership, (org, company.settings.get("activated_by", "")))
        if (
            company.settings.get("auto_send")
            and not content["warnings"]
            and actor
            and actor.active
            and actor.role == "admin"
        ):
            db.add(
                Approval(
                    org_id=org,
                    meeting_id=meeting_id,
                    version=row.version,
                    actor_id=actor.user_id,
                    kind="system_policy",
                    snapshot_hash=approval_hash(db, org, row),
                    policy_version=company.settings["policy_version"],
                    checks={"policy": company.settings, "schema": True, "references": True},
                )
            )
            db.flush()
            try:
                enqueue_deliveries(db, company, meeting_id, row)
                row.published, meeting.status = True, "ready"
            except __import__("fastapi").HTTPException:
                # No recipients is a review condition, never silent external delivery.
                meeting.status = "review_required"
