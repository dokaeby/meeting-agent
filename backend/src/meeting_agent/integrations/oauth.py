import time
from urllib.parse import urlencode

import httpx

from ..security import decrypt, encrypt

PROVIDERS = {
    "zoom": {
        "authorize": "https://zoom.us/oauth/authorize",
        "token": "https://zoom.us/oauth/token",
    },
    "kakao": {
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
    },
}


def credentials(settings, provider):
    return getattr(settings, f"{provider}_client_id"), getattr(
        settings, f"{provider}_client_secret"
    )


def redirect_uri(settings, provider):
    return f"{settings.public_url}/api/v1/integrations/{provider}/callback"


def authorize_url(settings, provider, state):
    client_id, _ = credentials(settings, provider)
    if not client_id or settings.provider_mode != "live":
        raise ValueError("연동 앱 자격증명이 필요합니다")
    query = {
        "client_id": client_id,
        "response_type": "code",
        "state": state,
        "redirect_uri": redirect_uri(settings, provider),
    }
    if provider == "kakao":
        query["scope"] = "talk_message"
    return PROVIDERS[provider]["authorize"] + "?" + urlencode(query)


def exchange(settings, provider, code=None, refresh=None, client=None):
    cid, secret = credentials(settings, provider)
    payload = {"grant_type": "refresh_token" if refresh else "authorization_code"}
    if refresh:
        payload["refresh_token"] = refresh
    else:
        payload.update(code=code, redirect_uri=redirect_uri(settings, provider))
    if provider == "kakao":
        payload.update(client_id=cid)
        if secret:
            payload["client_secret"] = secret
    owned_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        response = client.post(
            PROVIDERS[provider]["token"],
            data=payload,
            auth=(cid, secret) if provider == "zoom" else None,
        )
        response.raise_for_status()
        result = response.json()
        result["expires_at"] = time.time() + result.get("expires_in", 3600)
        if refresh and not result.get("refresh_token"):
            result["refresh_token"] = refresh
        return result
    finally:
        if owned_client:
            client.close()


def access_token(settings, integration):
    if integration.status != "connected":
        raise ValueError("연동이 해제되었습니다")
    secret = decrypt(integration.secret, settings.secret_key)
    if secret.get("expires_at", 0) < time.time() + 60:
        if not secret.get("refresh_token"):
            raise ValueError("계정을 다시 연결해 주세요")
        secret = exchange(settings, integration.provider, refresh=secret["refresh_token"])
        integration.secret = encrypt(secret, settings.secret_key)
    return secret["access_token"]
