from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select

from ..db import owned
from ..dependencies import audit, context, manager
from ..documents import render_pdf
from ..models import Approval, Membership, Minutes, Recipient, Transcript
from ..schemas import MinutesEdit, VersionInput
from ..security import snapshot
from ..storage import path_for, store
from .meetings import get_meeting
from .summary import validate_summary

router = APIRouter(prefix="/organizations/{org_id}/meetings/{meeting_id}")


def latest(db, org, meeting):
    return db.scalar(
        select(Minutes)
        .where(Minutes.org_id == org, Minutes.meeting_id == meeting)
        .order_by(Minutes.version.desc())
    )


def document(ctx, meeting_id, version=None):
    get_meeting(ctx, meeting_id)
    query = select(Minutes).where(Minutes.org_id == ctx.org.id, Minutes.meeting_id == meeting_id)
    if version:
        query = query.where(Minutes.version == version)
    if ctx.member.role == "member":
        query = query.where(Minutes.published.is_(True))
    row = ctx.db.scalar(query.order_by(Minutes.version.desc()))
    if not row:
        raise HTTPException(404, "회의록을 준비 중입니다")
    return row


def approval_hash(db, org, row):
    recipients = db.scalars(
        select(Recipient).where(Recipient.org_id == org, Recipient.meeting_id == row.meeting_id)
    ).all()
    return snapshot(
        {
            "content": row.content_hash,
            "version": row.version,
            "recipients": sorted(
                [(r.user_id, r.email_enabled, r.kakao_enabled) for r in recipients]
            ),
        }
    )


def approval_valid(db, org, row):
    approval = owned(db, Approval, org.id, meeting_id=row.meeting_id, version=row.version)
    if not approval or approval.snapshot_hash != approval_hash(db, org.id, row):
        return False
    actor = db.get(Membership, (org.id, approval.actor_id))
    if not actor or not actor.active or actor.role not in {"admin", "manager"}:
        return False
    if approval.kind == "system_policy":
        return (
            org.settings.get("auto_send")
            and org.settings.get("policy_version") == approval.policy_version
        )
    return True


@router.get("/minutes")
def read(ctx=Depends(context), meeting_id: str = ""):
    row = document(ctx, meeting_id)
    return {"version": row.version, "content": row.content, "published": row.published}


@router.put("/minutes")
def edit(meeting_id: str, data: MinutesEdit, request: Request, ctx=Depends(manager)):
    get_meeting(ctx, meeting_id, lock=True)
    old = document(ctx, meeting_id)
    if old.version != data.expected_version:
        raise HTTPException(409, "다른 사용자가 수정했습니다. 새로고침해 주세요")
    transcript = owned(ctx.db, Transcript, ctx.org.id, meeting_id=meeting_id)
    try:
        content = validate_summary(data.content.model_dump(mode="json"), transcript.segments)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    key = store(
        request.app.state.settings,
        ctx.org.id,
        meeting_id,
        render_pdf(content, request.app.state.settings),
        ".pdf",
    )
    row = Minutes(
        org_id=ctx.org.id,
        meeting_id=meeting_id,
        version=old.version + 1,
        content=content,
        content_hash=snapshot(content),
        pdf_key=key,
    )
    ctx.db.add(row)
    audit(ctx, "minutes.updated", meeting_id)
    return {"version": row.version, "content": content, "published": False}


@router.get("/minutes/{version}/pdf")
def pdf(meeting_id: str, version: int, request: Request, ctx=Depends(context)):
    row = document(ctx, meeting_id, version)
    path = path_for(request.app.state.settings, row.pdf_key)
    if not row.pdf_key or not path.is_file():
        raise HTTPException(404, "문서가 없습니다")
    return Response(
        path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="meeting-minutes.pdf"'},
    )


@router.post("/approve")
def approve(meeting_id: str, data: VersionInput, ctx=Depends(manager)):
    meeting = get_meeting(ctx, meeting_id, lock=True)
    row = document(ctx, meeting_id)
    if data.version != row.version:
        raise HTTPException(409, "최신 버전을 승인해 주세요")
    existing = owned(ctx.db, Approval, ctx.org.id, meeting_id=meeting_id, version=row.version)
    if existing:
        ctx.db.delete(existing)
        ctx.db.flush()
    ctx.db.add(
        Approval(
            org_id=ctx.org.id,
            meeting_id=meeting_id,
            version=row.version,
            snapshot_hash=approval_hash(ctx.db, ctx.org.id, row),
            actor_id=ctx.user.id,
            checks={"human_review": True},
        )
    )
    row.published, meeting.status = True, "ready"
    audit(ctx, "minutes.approved", meeting_id)
    return {"ok": True, "version": row.version}
