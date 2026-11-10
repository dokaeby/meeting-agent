from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select

from ..dependencies import current_user, database, memberships, user_json
from ..models import Job, Membership, Session, Token, User, now, uid
from ..schemas import Login, Register, Reset, ResetConfirm, TokenInput
from ..security import digest, password_hash, token, verify_password

router = APIRouter()


def issue(db, purpose, email, user_id=None, org_id=None, payload=None):
    raw = token()
    db.add(
        Token(
            token_hash=digest(raw),
            purpose=purpose,
            email=email,
            user_id=user_id,
            org_id=org_id,
            payload=payload or {},
            expires_at=now() + 3600,
        )
    )
    return raw


def consume(db, raw, purpose):
    row = db.scalar(select(Token).where(Token.token_hash == digest(raw)).with_for_update())
    if not row or row.purpose != purpose or row.expires_at < now():
        raise HTTPException(400, "토큰이 만료되었거나 유효하지 않습니다")
    return row


def mail_job(db, org_id, email, subject, body):
    from ..db import set_tenant

    set_tenant(db, org_id)
    db.add(
        Job(
            org_id=org_id,
            kind="mail",
            input_json={"email": email, "subject": subject, "body": body},
            dedupe_key=uid(),
        )
    )


def test_token(request, value):
    return {"test_token": value} if request.app.state.settings.environment == "test" else {}


@router.post("/auth/register", status_code=201)
def register(data: Register, request: Request, db=Depends(database)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "가입 정보를 확인해 주세요")
    user = User(email=email, name=data.name, password_hash=password_hash(data.password))
    db.add(user)
    db.flush()
    raw = issue(db, "verify", email, user.id)
    # Verification messages are queued in a dedicated system organization.
    mail_job(
        db, "system", email, "이메일 확인", f"{request.app.state.settings.public_url}/?verify={raw}"
    )
    return {**user_json(user), **test_token(request, raw)}


@router.post("/auth/verify-email")
def verify(data: TokenInput, db=Depends(database)):
    row = consume(db, data.token, "verify")
    db.get(User, row.user_id).verified = True
    db.delete(row)
    return {"ok": True}


@router.post("/auth/login")
def login(data: Login, request: Request, response: Response, db=Depends(database)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    # Match invalid-user hashing work to reduce account enumeration by timing.
    encoded = user.password_hash if user else password_hash("invalid-user-password")
    if not verify_password(data.password, encoded) or not user:
        raise HTTPException(401, "이메일 또는 비밀번호를 확인해 주세요")
    if not user.verified:
        raise HTTPException(403, "이메일 확인이 필요합니다")
    raw, csrf = token(), token()
    db.add(
        Session(
            token_hash=digest(raw),
            user_id=user.id,
            csrf_hash=digest(csrf),
            csrf_token=csrf,
            expires_at=now() + 86400,
        )
    )
    response.set_cookie(
        "ma_session",
        raw,
        httponly=True,
        secure=request.app.state.settings.environment == "production",
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return {"user": user_json(user), "csrf_token": csrf, "organizations": memberships(db, user)}


@router.get("/auth/session")
def session(request: Request, user=Depends(current_user), db=Depends(database)):
    session = db.get(Session, digest(request.cookies["ma_session"]))
    return {
        "user": user_json(user),
        "csrf_token": session.csrf_token,
        "organizations": memberships(db, user),
    }


@router.post("/auth/logout")
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(database)):
    db.delete(db.get(Session, digest(request.cookies["ma_session"])))
    response.delete_cookie("ma_session", path="/")
    return {"ok": True}


@router.post("/auth/password-reset", status_code=202)
def reset(data: Reset, request: Request, db=Depends(database)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user:
        raw = issue(db, "reset", user.email, user.id)
        mail_job(
            db,
            "system",
            user.email,
            "비밀번호 재설정",
            f"{request.app.state.settings.public_url}/?reset={raw}",
        )
    return {"ok": True}


@router.post("/auth/password-reset/confirm")
def confirm_reset(data: ResetConfirm, db=Depends(database)):
    row = consume(db, data.token, "reset")
    db.get(User, row.user_id).password_hash = password_hash(data.password)
    db.execute(delete(Session).where(Session.user_id == row.user_id))
    db.delete(row)
    return {"ok": True}


@router.post("/invitations/accept")
def accept(data: TokenInput, user=Depends(current_user), db=Depends(database)):
    row = consume(db, data.token, "invite")
    if row.email != user.email:
        raise HTTPException(403, "초대받은 이메일로 로그인해 주세요")
    member = db.get(Membership, (row.org_id, user.id))
    if not member:
        db.add(Membership(org_id=row.org_id, user_id=user.id, role=row.payload["role"]))
    elif not member.active:
        member.active, member.role = True, row.payload["role"]
    db.delete(row)
    return {"ok": True}
