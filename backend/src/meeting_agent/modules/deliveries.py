from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..db import owned
from ..dependencies import audit, manager
from ..models import Delivery, Job, Membership, Recipient
from ..schemas import RetryInput, VersionInput
from .meetings import get_meeting
from .minutes import approval_valid, document

router = APIRouter(prefix="/organizations/{org_id}")


def enqueue_deliveries(db, org, meeting_id, row):
    if not approval_valid(db, org, row):
        raise HTTPException(409, "최신 회의록과 수신자를 먼저 승인해 주세요")
    result = []
    for recipient in db.scalars(
        select(Recipient).where(Recipient.org_id == org.id, Recipient.meeting_id == meeting_id)
    ):
        member = db.get(Membership, (org.id, recipient.user_id))
        if not member or not member.active:
            continue
        for channel, enabled in [
            ("email", recipient.email_enabled),
            ("kakao", recipient.kakao_enabled),
        ]:
            if not enabled:
                continue
            delivery = owned(
                db,
                Delivery,
                org.id,
                meeting_id=meeting_id,
                version=row.version,
                user_id=recipient.user_id,
                channel=channel,
            )
            if not delivery:
                delivery = Delivery(
                    org_id=org.id,
                    meeting_id=meeting_id,
                    version=row.version,
                    user_id=recipient.user_id,
                    channel=channel,
                )
                db.add(delivery)
                db.flush()
                db.add(
                    Job(
                        org_id=org.id,
                        meeting_id=meeting_id,
                        kind="delivery",
                        input_json={"delivery_id": delivery.id},
                        dedupe_key=f"delivery:{delivery.id}",
                    )
                )
            result.append({"id": delivery.id, "channel": channel})
    if not result:
        raise HTTPException(422, "발송할 수신자를 설정해 주세요")
    return {"items": result}


@router.post("/meetings/{meeting_id}/send", status_code=202)
def send(meeting_id: str, data: VersionInput, ctx=Depends(manager)):
    get_meeting(ctx, meeting_id, lock=True)
    row = document(ctx, meeting_id)
    if row.version != data.version:
        raise HTTPException(409, "최신 버전을 선택해 주세요")
    result = enqueue_deliveries(ctx.db, ctx.org, meeting_id, row)
    audit(ctx, "delivery.requested", meeting_id)
    return result


@router.get("/deliveries")
def deliveries(ctx=Depends(manager)):
    return {
        "items": [
            {
                k: getattr(row, k)
                for k in (
                    "id",
                    "meeting_id",
                    "version",
                    "user_id",
                    "channel",
                    "status",
                    "attempts",
                    "error",
                )
            }
            for row in ctx.db.scalars(select(Delivery).where(Delivery.org_id == ctx.org.id))
        ]
    }


@router.post("/deliveries/{delivery_id}/retry", status_code=202)
def retry(delivery_id: str, data: RetryInput, ctx=Depends(manager)):
    row = ctx.db.scalar(
        select(Delivery)
        .where(Delivery.org_id == ctx.org.id, Delivery.id == delivery_id)
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "찾을 수 없습니다")
    get_meeting(ctx, row.meeting_id, lock=True)
    latest = document(ctx, row.meeting_id)
    if row.version != latest.version or not approval_valid(ctx.db, ctx.org, latest):
        raise HTTPException(409, "최신 승인 상태를 확인해 주세요")
    if row.status not in {"failed", "unknown"}:
        raise HTTPException(409, "재시도 가능한 상태가 아닙니다")
    if row.status == "unknown" and not data.acknowledge_duplicate_risk:
        raise HTTPException(409, "중복 발송 위험을 확인해 주세요")
    row.status = "pending"
    ctx.db.add(
        Job(
            org_id=ctx.org.id,
            meeting_id=row.meeting_id,
            kind="delivery",
            input_json={"delivery_id": row.id},
            dedupe_key=f"retry:{row.id}:{row.attempts}",
        )
    )
    audit(ctx, "delivery.retry", row.id)
    return {"ok": True}
