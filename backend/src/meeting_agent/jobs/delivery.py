import smtplib

import httpx
from sqlalchemy import select

from ..db import owned, transaction
from ..integrations.kakao import send_kakao
from ..integrations.mail import send_mail
from ..models import (
    Delivery,
    Integration,
    Meeting,
    Membership,
    Organization,
    Recipient,
    User,
)
from ..modules.minutes import approval_valid, latest
from ..storage import path_for


def deliver(settings, factory, org, job_id, fence, payload):
    from .runner import assert_claim

    with transaction(factory, org) as db:
        job = assert_claim(db, org, job_id, fence)
        delivery = db.scalar(
            select(Delivery)
            .where(Delivery.org_id == org, Delivery.id == payload["delivery_id"])
            .with_for_update()
        )
        if not delivery or delivery.status in {"accepted", "unknown", "cancelled", "skipped"}:
            job.state = "done"
            return
        if delivery.status == "sending":
            delivery.status, job.state = "unknown", "done"
            return
        meeting = owned(db, Meeting, org, id=delivery.meeting_id)
        member = db.get(Membership, (org, delivery.user_id))
        recipient = owned(
            db, Recipient, org, meeting_id=delivery.meeting_id, user_id=delivery.user_id
        )
        row = latest(db, org, delivery.meeting_id)
        company = db.get(Organization, org)
        enabled = recipient and (
            recipient.email_enabled if delivery.channel == "email" else recipient.kakao_enabled
        )
        if (
            not meeting
            or meeting.deleted
            or not member
            or not member.active
            or not enabled
            or row.version != delivery.version
            or not approval_valid(db, company, row)
        ):
            delivery.status, job.state = "cancelled", "done"
            return
        integration = db.scalar(
            select(Integration)
            .where(
                Integration.org_id == org,
                Integration.user_id == delivery.user_id,
                Integration.provider == "kakao",
            )
            .with_for_update()
        )
        if delivery.channel == "kakao" and (not integration or integration.status != "connected"):
            delivery.status, job.state = "skipped", "done"
            return
        user = db.get(User, delivery.user_id)
        email, title, body, key = (
            user.email,
            row.content["title"],
            row.content["overview"]["text"],
            row.pdf_key,
        )
        delivery_id, channel = delivery.id, delivery.channel
        delivery.status, delivery.attempts = "sending", delivery.attempts + 1
        # Detached credential is serialized under a row lock before the external effect.
        if integration:
            from ..integrations.oauth import access_token

            if settings.provider_mode == "live":
                access_token(settings, integration)
    link = f"{settings.public_url}/?org={org}&meeting={meeting.id}"
    try:
        if channel == "email":
            result = send_mail(
                settings,
                email,
                title,
                body + "\n\n" + link,
                path_for(settings, key).read_bytes(),
                delivery_id,
            )
        else:
            result = send_kakao(settings, integration, title, body, link)
        status, error = "accepted", ""
    except (httpx.TimeoutException, smtplib.SMTPServerDisconnected, TimeoutError, OSError):
        status, error, result = "unknown", "delivery_outcome_unknown", ""
    except (ValueError, httpx.HTTPStatusError, smtplib.SMTPException):
        status, error, result = "failed", "provider_rejected", ""
    with transaction(factory, org) as db:
        job = assert_claim(db, org, job_id, fence)
        delivery = owned(db, Delivery, org, id=delivery_id)
        delivery.status, delivery.provider_id, delivery.error = status, result, error
        job.state = "done"
        meeting = owned(db, Meeting, org, id=delivery.meeting_id)
        if not meeting.deleted:
            pending = db.scalar(
                select(Delivery.id).where(
                    Delivery.org_id == org,
                    Delivery.meeting_id == meeting.id,
                    Delivery.status.in_(["pending", "sending"]),
                )
            )
            if not pending:
                meeting.status = "completed"
