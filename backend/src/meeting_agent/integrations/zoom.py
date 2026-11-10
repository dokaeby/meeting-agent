import hashlib
import hmac
import ipaddress
import socket
import time
from urllib.parse import urlsplit

import httpx


def verify_webhook(body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    try:
        if not secret or abs(time.time() - int(timestamp)) > 300:
            return False
        expected = (
            "v0="
            + hmac.new(
                secret.encode(), b"v0:" + timestamp.encode() + b":" + body, hashlib.sha256
            ).hexdigest()
        )
        return hmac.compare_digest(expected, signature)
    except (ValueError, TypeError):
        return False


def validate_download_url(url: str, resolve=True):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not any(host == d or host.endswith("." + d) for d in ("zoom.us", "zoom.com"))
    ):
        raise ValueError("untrusted Zoom download host")
    if resolve:
        for address in socket.getaddrinfo(host, 443):
            if not ipaddress.ip_address(address[4][0]).is_global:
                raise ValueError("non-public Zoom download address")
    return url


def download(settings, url, access_token):
    validate_download_url(url)
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        with client.stream(
            "GET", url, headers={"Authorization": f"Bearer {access_token}"}
        ) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for part in response.iter_bytes():
                size += len(part)
                if size > settings.max_upload_bytes:
                    raise ValueError("Zoom source exceeds size limit")
                chunks.append(part)
    return b"".join(chunks)
