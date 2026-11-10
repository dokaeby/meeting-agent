import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from .db import set_tenant
from .models import Audit, Membership, Organization, Session, User, now
from .security import digest


def database(request: Request):
    with request.app.state.factory() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def current_user(request: Request, db: DBSession = Depends(database)):
    session = db.get(Session, digest(request.cookies.get("ma_session", "")))
    if not session or session.expires_at < now():
        raise HTTPException(401, "로그인이 필요합니다")
    user = db.get(User, session.user_id)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = digest(request.headers.get("X-CSRF-Token", ""))
        if not secrets.compare_digest(csrf, session.csrf_hash):
            raise HTTPException(403, "CSRF 검증 실패")
    return user


@dataclass
class Context:
    db: DBSession
    user: User
    org: Organization
    member: Membership


def context(org_id: str, db: DBSession = Depends(database), user=Depends(current_user)):
    member = db.get(Membership, (org_id, user.id))
    if not member or not member.active:
        raise HTTPException(404, "찾을 수 없습니다")
    org = db.get(Organization, org_id)
    set_tenant(db, org_id)
    return Context(db, user, org, member)


def manager(ctx: Context = Depends(context)):
    if ctx.member.role not in {"admin", "manager"}:
        raise HTTPException(403, "회의 관리 권한이 필요합니다")
    return ctx


def admin(ctx: Context = Depends(context)):
    if ctx.member.role != "admin":
        raise HTTPException(403, "관리자 권한이 필요합니다")
    return ctx


def audit(ctx: Context, action: str, target: str):
    ctx.db.add(Audit(org_id=ctx.org.id, actor_id=ctx.user.id, action=action, target_id=target))


def user_json(user):
    return {"id": user.id, "email": user.email, "name": user.name, "verified": user.verified}


def memberships(db, user):
    return [
        {"id": org.id, "name": org.name, "role": member.role}
        for member, org in db.execute(
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.org_id)
            .where(Membership.user_id == user.id, Membership.active.is_(True))
        )
    ]
