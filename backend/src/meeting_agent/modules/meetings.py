from datetime import timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import delete, func, select

from ..db import owned
from ..dependencies import audit, context, manager
from ..models import Job, Meeting, Membership, Minutes, Recipient, Transcript
from ..schemas import MeetingInput, RecipientInput
from ..security import digest
from ..storage import store

router = APIRouter(prefix="/organizations/{org_id}")


def get_meeting(ctx, meeting_id, lock=False):
    statement = select(Meeting).where(
        Meeting.org_id == ctx.org.id, Meeting.id == meeting_id, Meeting.deleted.is_(False)
    )
    if lock:
        statement = statement.with_for_update()
    meeting = ctx.db.scalar(statement)
    if not meeting:
        raise HTTPException(404, "찾을 수 없습니다")
    if ctx.member.role == "member" and not owned(
        ctx.db, Recipient, ctx.org.id, meeting_id=meeting_id, user_id=ctx.user.id
    ):
        raise HTTPException(404, "찾을 수 없습니다")
    return meeting


def meeting_json(row):
    return {k: getattr(row, k) for k in ("id", "title", "status", "start_at", "timezone")}


@router.get("/meetings")
def meetings(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    status: str | None = None,
    ctx=Depends(context),
):
    query = select(Meeting).where(Meeting.org_id == ctx.org.id, Meeting.deleted.is_(False))
    if ctx.member.role == "member":
        query = query.where(
            Meeting.id.in_(
                select(Recipient.meeting_id).where(
                    Recipient.org_id == ctx.org.id, Recipient.user_id == ctx.user.id
                )
            ),
            Meeting.id.in_(
                select(Minutes.meeting_id).where(
                    Minutes.org_id == ctx.org.id, Minutes.published.is_(True)
                )
            ),
        )
    if status:
        query = query.where(Meeting.status == status)
    total = ctx.db.scalar(select(func.count()).select_from(query.subquery()))
    rows = ctx.db.scalars(query.order_by(Meeting.created_at.desc()).offset(offset).limit(limit))
    return {
        "items": [meeting_json(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.post("/meetings", status_code=201)
def create(data: MeetingInput, ctx=Depends(manager)):
    meeting = Meeting(
        org_id=ctx.org.id,
        title=data.title,
        start_at=data.start_at.astimezone(timezone.utc).isoformat(),
        timezone=data.timezone,
    )
    ctx.db.add(meeting)
    ctx.db.flush()
    audit(ctx, "meeting.created", meeting.id)
    return meeting_json(meeting)


@router.get("/meetings/{meeting_id}")
def detail(meeting_id: str, ctx=Depends(context)):
    meeting = get_meeting(ctx, meeting_id)
    if ctx.member.role == "member":
        if not ctx.db.scalar(
            select(Minutes.id).where(
                Minutes.org_id == ctx.org.id,
                Minutes.meeting_id == meeting_id,
                Minutes.published.is_(True),
            )
        ):
            raise HTTPException(404, "찾을 수 없습니다")
    recipients = ctx.db.scalars(
        select(Recipient).where(Recipient.org_id == ctx.org.id, Recipient.meeting_id == meeting_id)
    )
    return {
        **meeting_json(meeting),
        "recipients": [
            {"user_id": r.user_id, "email": r.email_enabled, "kakao": r.kakao_enabled}
            for r in recipients
        ],
    }


@router.put("/meetings/{meeting_id}/recipients")
def recipients(meeting_id: str, data: list[RecipientInput], ctx=Depends(manager)):
    get_meeting(ctx, meeting_id, lock=True)
    if len(data) > 100 or len({r.user_id for r in data}) != len(data):
        raise HTTPException(422, "수신자는 중복 없이 최대 100명입니다")
    for recipient in data:
        member = ctx.db.get(Membership, (ctx.org.id, recipient.user_id))
        if not member or not member.active:
            raise HTTPException(422, "같은 회사의 활성 직원만 지정할 수 있습니다")
    ctx.db.execute(
        delete(Recipient).where(Recipient.org_id == ctx.org.id, Recipient.meeting_id == meeting_id)
    )
    for item in data:
        ctx.db.add(
            Recipient(
                org_id=ctx.org.id,
                meeting_id=meeting_id,
                user_id=item.user_id,
                email_enabled=item.email,
                kakao_enabled=item.kakao,
            )
        )
    for row in ctx.db.scalars(
        select(Minutes).where(Minutes.org_id == ctx.org.id, Minutes.meeting_id == meeting_id)
    ):
        row.published = False
    audit(ctx, "recipients.updated", meeting_id)
    return {"ok": True}


@router.post("/meetings/{meeting_id}/source", status_code=202)
def source(meeting_id: str, request: Request, file: UploadFile = File(), ctx=Depends(manager)):
    meeting = get_meeting(ctx, meeting_id, lock=True)
    settings = request.app.state.settings
    if settings.provider_mode != "test" and not ctx.org.settings.get("ai_consent"):
        raise HTTPException(422, "설정에서 외부 AI 처리 동의를 먼저 확인해 주세요")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".txt", ".vtt", ".srt", ".mp3", ".m4a", ".wav"}:
        raise HTTPException(422, "지원하지 않는 파일입니다")
    content = file.file.read(settings.max_upload_bytes + 1)
    if not content or len(content) > settings.max_upload_bytes:
        raise HTTPException(422, "파일 크기 제한을 확인해 주세요")
    if ext in {".txt", ".vtt", ".srt"}:
        try:
            text = content.decode("utf-8-sig")
            if len(text) > settings.max_transcript_chars or "\x00" in text:
                raise ValueError()
        except (UnicodeError, ValueError) as exc:
            raise HTTPException(422, "UTF-8 텍스트와 길이를 확인해 주세요") from exc
    existing = ctx.db.scalar(
        select(Job).where(
            Job.org_id == ctx.org.id,
            Job.meeting_id == meeting_id,
            Job.kind == "pipeline",
            Job.state.in_(["pending", "running", "retry_wait"]),
        )
    )
    if existing:
        raise HTTPException(409, "이미 처리 중입니다")
    key = store(settings, ctx.org.id, meeting.id, content, ext)
    job = Job(
        org_id=ctx.org.id,
        meeting_id=meeting.id,
        kind="pipeline",
        input_json={"source_key": key, "generation": meeting.generation},
        dedupe_key=f"source:{meeting.id}:{digest(content.hex())}",
    )
    previous = owned(ctx.db, Job, ctx.org.id, dedupe_key=job.dedupe_key)
    if previous:
        return {"job_id": previous.id, "state": previous.state}
    ctx.db.add(job)
    ctx.db.flush()
    meeting.status = "transcribing"
    audit(ctx, "source.uploaded", meeting_id)
    return {"job_id": job.id, "state": job.state}


@router.get("/meetings/{meeting_id}/transcript")
def transcript(meeting_id: str, ctx=Depends(manager)):
    get_meeting(ctx, meeting_id)
    row = owned(ctx.db, Transcript, ctx.org.id, meeting_id=meeting_id)
    return {"segments": row.segments if row else []}


@router.get("/meetings/{meeting_id}/jobs")
def jobs(meeting_id: str, ctx=Depends(manager)):
    get_meeting(ctx, meeting_id)
    return {
        "items": [
            {"id": j.id, "kind": j.kind, "state": j.state, "attempts": j.attempts}
            for j in ctx.db.scalars(
                select(Job).where(Job.org_id == ctx.org.id, Job.meeting_id == meeting_id)
            )
        ]
    }


@router.delete("/meetings/{meeting_id}")
def remove(meeting_id: str, ctx=Depends(manager)):
    meeting = get_meeting(ctx, meeting_id, lock=True)
    meeting.deleted = True
    meeting.generation += 1
    audit(ctx, "meeting.deleted", meeting_id)
    return {"ok": True}
