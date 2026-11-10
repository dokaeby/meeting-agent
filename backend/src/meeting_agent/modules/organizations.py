from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select

from ..dependencies import admin, audit, context, current_user, database, memberships, user_json
from ..models import Membership, Organization, Usage, User, now
from ..schemas import Invite, MemberUpdate, OrgInput, Policy
from .identity import issue, mail_job, test_token

router = APIRouter()


@router.get("/organizations")
def organizations(user=Depends(current_user), db=Depends(database)):
    return {"items": memberships(db, user)}


@router.post("/organizations", status_code=201)
def create(data: OrgInput, user=Depends(current_user), db=Depends(database)):
    org = Organization(name=data.name)
    db.add(org)
    db.flush()
    db.add(Membership(org_id=org.id, user_id=user.id, role="admin"))
    return {"id": org.id, "name": org.name, "role": "admin"}


@router.get("/organizations/{org_id}/members")
def members(ctx=Depends(context)):
    rows = ctx.db.execute(
        select(Membership, User).join(User).where(Membership.org_id == ctx.org.id)
    )
    return {
        "items": [
            {
                **user_json(user),
                "role": member.role,
                "active": member.active,
                "aliases": member.aliases,
            }
            for member, user in rows
        ]
    }


@router.patch("/organizations/{org_id}/members/{user_id}")
def update_member(user_id: str, data: MemberUpdate, ctx=Depends(admin)):
    ctx.db.scalar(select(Organization).where(Organization.id == ctx.org.id).with_for_update())
    member = ctx.db.get(Membership, (ctx.org.id, user_id))
    if not member:
        raise HTTPException(404, "찾을 수 없습니다")
    if member.role == "admin" and (not data.active or data.role != "admin"):
        count = ctx.db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.org_id == ctx.org.id,
                Membership.active.is_(True),
                Membership.role == "admin",
            )
        )
        if count <= 1:
            raise HTTPException(409, "마지막 관리자는 삭제하거나 강등할 수 없습니다")
    member.role, member.active, member.aliases = data.role, data.active, data.aliases
    audit(ctx, "member.updated", user_id)
    return {"ok": True}


@router.post("/organizations/{org_id}/invitations", status_code=201)
def invite(data: Invite, request: Request, ctx=Depends(admin)):
    raw = issue(
        ctx.db, "invite", str(data.email).lower(), org_id=ctx.org.id, payload={"role": data.role}
    )
    mail_job(
        ctx.db,
        ctx.org.id,
        str(data.email),
        "Meeting Agent 초대",
        f"{request.app.state.settings.public_url}/?invite={raw}",
    )
    audit(ctx, "invitation.created", str(data.email))
    return {"ok": True, **test_token(request, raw)}


@router.get("/organizations/{org_id}/settings")
def settings(ctx=Depends(context)):
    return ctx.org.settings


@router.patch("/organizations/{org_id}/settings")
def policy(data: Policy, ctx=Depends(admin)):
    if data.auto_send and not data.ai_consent:
        raise HTTPException(422, "외부 AI 처리와 자동 발송 정책에 동의해 주세요")
    ctx.db.scalar(select(Organization).where(Organization.id == ctx.org.id).with_for_update())
    ctx.org.settings = {
        **data.model_dump(),
        "policy_version": ctx.org.settings.get("policy_version", 0) + 1,
        "activated_by": ctx.user.id,
        "activated_at": now(),
    }
    audit(ctx, "policy.updated", ctx.org.id)
    return ctx.org.settings


@router.get("/organizations/{org_id}/usage")
def usage(ctx=Depends(context)):
    rows = ctx.db.scalars(select(Usage).where(Usage.org_id == ctx.org.id)).all()
    return {
        "items": [
            {
                "period": r.period,
                "meetings": r.meetings,
                "tokens": r.tokens,
                "stt_seconds": r.stt_seconds,
                "bytes": r.bytes,
            }
            for r in rows
        ],
        "monthly_meetings": ctx.org.settings.get("monthly_meetings", 100),
    }
