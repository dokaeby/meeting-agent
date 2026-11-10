import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import select
from test_meetings import create_meeting

from meeting_agent.db import transaction
from meeting_agent.integrations.groq import Groq
from meeting_agent.jobs.retention import cleanup
from meeting_agent.jobs.runner import claim
from meeting_agent.models import (
    Integration,
    IntegrationAccount,
    Job,
    Meeting,
    Organization,
    now,
)
from meeting_agent.storage import path_for, store


def signed(client, payload):
    body = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    client.app.state.settings.zoom_webhook_secret = "test-hook"
    sig = hmac.new(b"test-hook", b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/webhooks/zoom",
        content=body,
        headers={"x-zm-request-timestamp": stamp, "x-zm-signature": "v0=" + sig},
    )


def test_old_zoom_identity_cannot_ingest(client, owner):
    user, org = owner
    with transaction(client.app.state.factory, org) as db:
        company = db.get(Organization, org)
        company.settings = {**company.settings, "ai_consent": True}
        db.add(
            Integration(
                org_id=org,
                user_id=user["id"],
                provider="zoom",
                external_account="new",
                external_user="new-host",
                secret="unused",
            )
        )
        db.add(
            IntegrationAccount(
                provider="zoom",
                external_account="old",
                org_id=org,
                external_users={"old-host": user["id"]},
            )
        )
    assert (
        signed(
            client,
            {
                "event": "recording.completed",
                "payload": {
                    "account_id": "old",
                    "object": {
                        "uuid": "old-meeting",
                        "host_id": "old-host",
                        "topic": "Old",
                        "start_time": "2026-11-10",
                    },
                },
            },
        ).status_code
        == 200
    )
    with transaction(client.app.state.factory, org) as db:
        assert db.scalar(select(Meeting).where(Meeting.org_id == org)) is None


def test_transcript_event_reactivates_failed_collection(client, owner):
    user, org = owner
    with transaction(client.app.state.factory, org) as db:
        company = db.get(Organization, org)
        company.settings = {**company.settings, "ai_consent": True}
        db.add(
            Integration(
                org_id=org,
                user_id=user["id"],
                provider="zoom",
                external_account="a",
                external_user="host",
                secret="unused",
            )
        )
        db.add(
            IntegrationAccount(
                provider="zoom",
                external_account="a",
                org_id=org,
                external_users={"host": user["id"]},
            )
        )
    payload = {
        "event": "recording.completed",
        "payload": {
            "account_id": "a",
            "object": {
                "uuid": "meeting",
                "host_id": "host",
                "topic": "Test",
                "start_time": "2026-11-10",
            },
        },
    }
    signed(client, payload)
    with transaction(client.app.state.factory, org) as db:
        job = db.scalar(select(Job).where(Job.org_id == org, Job.kind == "zoom"))
        job.state = "failed"
    payload["event"] = "recording.transcript_completed"
    signed(client, payload)
    with transaction(client.app.state.factory, org) as db:
        assert (
            db.scalar(select(Job).where(Job.org_id == org, Job.kind == "zoom")).state == "pending"
        )


def test_retention_keeps_transcript_until_document_expiry(client, owner):
    _, org = owner
    meeting = create_meeting(client, org)
    settings = client.app.state.settings
    txt = store(settings, org, meeting, b"notes", ".txt")
    audio = store(settings, org, meeting, b"audio", ".m4a")
    with transaction(client.app.state.factory, org) as db:
        db.get(Meeting, meeting).created_at = now() - 8 * 86400
    cleanup(settings, client.app.state.factory)
    assert path_for(settings, txt).is_file()
    assert not path_for(settings, audio).exists()


def test_expired_claim_rejects_old_worker(client, owner):
    _, org = owner
    with transaction(client.app.state.factory, org) as db:
        job = Job(org_id=org, kind="mail", input_json={}, dedupe_key="claim")
        db.add(job)
        db.flush()
        job_id = job.id
    factory = client.app.state.factory
    first = claim(factory, org, job_id)
    assert claim(factory, org, job_id) is None
    with transaction(factory, org) as db:
        db.get(Job, job_id).lease_until = 0
    second = claim(factory, org, job_id)
    assert second == first + 1
    from meeting_agent.jobs.runner import assert_claim

    with transaction(factory, org) as db:
        with pytest.raises(ValueError, match="stale"):
            assert_claim(db, org, job_id, first)


def test_provider_checks_cancellation_before_each_chunk(client):
    import httpx

    settings = client.app.state.settings.model_copy(
        update={"provider_mode": "live", "groq_key": "test"}
    )
    calls = []

    def checkpoint():
        calls.append("checkpoint")
        if len(calls) > 1:
            raise ValueError("cancelled")

    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"title": "t", "overview": {"text": "test", "evidence_ids": ["s1"]}}
                    )
                }
            }
        ]
    }
    provider = Groq(
        settings,
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))),
        checkpoint=checkpoint,
    )
    segments = [{"id": "s1", "text": "x" * 19000}, {"id": "s2", "text": "y" * 19000}]
    with pytest.raises(ValueError, match="cancelled"):
        provider.summarize(segments, "title", [])
