import hashlib
import hmac
import json
import time

import httpx
import pytest

from meeting_agent.integrations.groq import Groq
from meeting_agent.integrations.zoom import validate_download_url, verify_webhook


def test_zoom_signature_and_replay():
    body = b'{"event":"recording.completed"}'
    stamp = str(int(time.time()))
    signature = (
        "v0="
        + hmac.new(b"secret", b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    )
    assert verify_webhook(body, stamp, signature, "secret")
    assert not verify_webhook(body, "1", signature, "secret")
    assert not verify_webhook(body + b"x", stamp, signature, "secret")


@pytest.mark.parametrize(
    "url",
    [
        "http://zoom.us/x",
        "https://127.0.0.1/x",
        "https://zoom.us.evil.com/x",
        "https://user:secret@zoom.us/x",
    ],
)
def test_download_url_rejects_untrusted(url):
    with pytest.raises(ValueError):
        validate_download_url(url, resolve=False)


def test_groq_summary_contract(client):
    body = {"title": "회의", "overview": {"text": "출시 준비", "evidence_ids": ["s1"]}}

    def handler(request):
        assert request.headers["authorization"] == "Bearer test"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(body)}}],
                "usage": {"total_tokens": 22},
            },
        )

    settings = client.app.state.settings.model_copy(
        update={"groq_key": "test", "provider_mode": "live"}
    )
    provider = Groq(settings, httpx.Client(transport=httpx.MockTransport(handler)))
    result, usage = provider.summarize([{"id": "s1", "text": "출시 준비"}], "회의", [])
    assert result["title"] == "회의"
    assert usage == 22
