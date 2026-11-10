import hashlib
import hmac
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from ..db import owned, set_tenant
from ..dependencies import audit, context, current_user, database
from ..integrations import oauth
from ..integrations.zoom import verify_webhook
from ..models import (
    Integration,
    IntegrationAccount,
    Job,
    Meeting,
    Membership,
    Token,
    WebhookReceipt,
)
from ..security import digest, encrypt, token
from .identity import consume

router = APIRouter()


def provider_allowed(provider):
    if provider not in oauth.PROVIDERS:
        raise HTTPException(404, "지원하지 않는 연동")


@router.get("/organizations/{org_id}/integrations")
def list_integrations(ctx=Depends(context)):
    rows = ctx.db.scalars(select(Integration).where(Integration.org_id == ctx.org.id))
    return {
        "items": [
            {
                "id": r.id,
                "provider": r.provider,
                "user_id": r.user_id,
                "status": r.status,
                "external_user": r.external_user,
            }
            for r in rows
            if ctx.member.role != "member" or r.user_id == ctx.user.id
        ]
    }


@router.post("/organizations/{org_id}/integrations/{provider}/authorize")
def authorize(provider: str, request: Request, ctx=Depends(context)):
    from ..models import now

    provider_allowed(provider)
    if provider == "zoom" and ctx.member.role not in {"admin", "manager"}:
        raise HTTPException(403, "회의 관리 권한이 필요합니다")
    raw = token()
    try:
        url = oauth.authorize_url(request.app.state.settings, provider, raw)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    ctx.db.add(
        Token(
            token_hash=digest(raw),
            user_id=ctx.user.id,
            org_id=ctx.org.id,
            email=ctx.user.email,
            purpose="oauth",
            payload={"provider": provider},
            expires_at=now() + 600,
        )
    )
    return {"authorize_url": url}


@router.get("/integrations/{provider}/callback")
def callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    user=Depends(current_user),
    db=Depends(database),
):
    provider_allowed(provider)
    row = consume(db, state, "oauth")
    if row.user_id != user.id or row.payload["provider"] != provider:
        raise HTTPException(403, "연동 요청이 일치하지 않습니다")
    member = db.get(Membership, (row.org_id, user.id))
    if (
        not member
        or not member.active
        or (provider == "zoom" and member.role not in {"admin", "manager"})
    ):
        raise HTTPException(403, "연동 권한이 없습니다")
    settings = request.app.state.settings
    org = row.org_id
    # Consume state before the external request, including failed exchanges.
    db.delete(row)
    db.commit()
    set_tenant(db, org)
    try:
        secret = oauth.exchange(settings, provider, code=code)
        with httpx.Client(timeout=30) as client:
            endpoint = (
                "https://api.zoom.us/v2/users/me"
                if provider == "zoom"
                else "https://kapi.kakao.com/v2/user/me"
            )
            result = client.get(
                endpoint, headers={"Authorization": f"Bearer {secret['access_token']}"}
            )
            result.raise_for_status()
            external = result.json()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, "외부 계정 연결에 실패했습니다. 다시 연결해 주세요") from exc
    account = str(external.get("account_id", external["id"]))
    external_user = str(external["id"])
    directory = db.get(IntegrationAccount, (provider, account))
    if directory and directory.org_id != org:
        raise HTTPException(409, "이 외부 계정은 다른 회사에 연결되어 있습니다")
    if not directory:
        directory = IntegrationAccount(
            provider=provider, external_account=account, org_id=org, external_users={}
        )
        db.add(directory)
    mapping = directory.external_users
    if external_user in mapping and mapping[external_user] != user.id:
        raise HTTPException(409, "다른 직원이 연결한 외부 계정입니다")
    directory.external_users = {**mapping, external_user: user.id}
    integration = owned(db, Integration, org, user_id=user.id, provider=provider)
    if integration and (integration.external_account, integration.external_user) != (
        account,
        external_user,
    ):
        old = db.get(IntegrationAccount, (provider, integration.external_account))
        if old:
            old.external_users = {
                k: v for k, v in old.external_users.items() if k != integration.external_user
            }
    if not integration:
        integration = Integration(
            org_id=org,
            user_id=user.id,
            provider=provider,
            external_account=account,
            external_user=external_user,
            secret="",
        )
        db.add(integration)
    integration.secret, integration.status = encrypt(secret, settings.secret_key), "connected"
    integration.external_account, integration.external_user = account, external_user
    return RedirectResponse(
        f"{settings.public_url}/?org={org}&connected={provider}", status_code=303
    )


@router.delete("/organizations/{org_id}/integrations/{integration_id}")
def disconnect(integration_id: str, ctx=Depends(context)):
    row = owned(ctx.db, Integration, ctx.org.id, id=integration_id)
    if not row:
        raise HTTPException(404, "찾을 수 없습니다")
    if ctx.member.role != "admin" and row.user_id != ctx.user.id:
        raise HTTPException(403, "본인 연동만 해제할 수 있습니다")
    row.status, row.secret = "disconnected", ""
    audit(ctx, "integration.disconnected", row.id)
    return {"ok": True}


@router.post("/webhooks/zoom")
async def zoom_webhook(request: Request, db=Depends(database)):
    settings = request.app.state.settings
    body = await request.body()
    if len(body) > 1024 * 1024:
        raise HTTPException(413, "이벤트 크기 제한 초과")
    if not verify_webhook(
        body,
        request.headers.get("x-zm-request-timestamp", ""),
        request.headers.get("x-zm-signature", ""),
        settings.zoom_webhook_secret,
    ):
        raise HTTPException(401, "웹훅 서명 검증 실패")
    try:
        payload = json.loads(body)
        event = payload["event"]
    except (ValueError, KeyError):
        raise HTTPException(422, "잘못된 이벤트")
    if event == "endpoint.url_validation":
        plain = payload["payload"]["plainToken"]
        return {
            "plainToken": plain,
            "encryptedToken": hmac.new(
                settings.zoom_webhook_secret.encode(), plain.encode(), hashlib.sha256
            ).hexdigest(),
        }
    dedupe = digest(body.decode())
    if db.get(WebhookReceipt, dedupe):
        return {"ok": True}
    obj = payload.get("payload", {}).get("object", {})
    account = str(payload.get("payload", {}).get("account_id", ""))
    directory = db.get(IntegrationAccount, ("zoom", account))
    if not directory or event not in {"recording.completed", "recording.transcript_completed"}:
        return {"ok": True}
    org = directory.org_id
    set_tenant(db, org)
    owner_id = directory.external_users.get(str(obj.get("host_id", "")))
    connection = owned(db, Integration, org, provider="zoom", user_id=owner_id)
    member = db.get(Membership, (org, owner_id)) if owner_id else None
    if (
        not connection
        or connection.status != "connected"
        or not member
        or not member.active
        or connection.external_account != account
        or connection.external_user != str(obj.get("host_id", ""))
    ):
        return {"ok": True}
    from ..models import Organization

    company = db.get(Organization, org)
    if not company.settings.get("ai_consent"):
        return {"ok": True}
    external_id = str(obj.get("uuid", ""))
    if not external_id:
        raise HTTPException(422, "회의 UUID 누락")
    meeting = owned(db, Meeting, org, external_id=external_id)
    if not meeting:
        meeting = Meeting(
            org_id=org,
            external_id=external_id,
            host_id=owner_id,
            title=str(obj.get("topic", "Zoom 회의"))[:200],
            start_at=obj.get("start_time", ""),
            timezone="Asia/Seoul",
        )
        db.add(meeting)
        db.flush()
    db.add(WebhookReceipt(dedupe_hash=dedupe))
    # One source job per meeting; either event may arrive first.
    source_job = owned(db, Job, org, dedupe_key=f"zoom:{meeting.id}")
    if not source_job:
        from ..models import now

        db.add(
            Job(
                org_id=org,
                meeting_id=meeting.id,
                kind="zoom",
                dedupe_key=f"zoom:{meeting.id}",
                input_json={
                    "external_id": external_id,
                    "integration_id": connection.id,
                    "generation": meeting.generation,
                    "received_at": now(),
                },
            )
        )
    elif event == "recording.transcript_completed" and source_job.state in {"failed", "retry_wait"}:
        from ..models import now

        source_job.state, source_job.attempts, source_job.next_at = "pending", 0, now()
    return {"ok": True}
