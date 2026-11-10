from sqlalchemy import or_, select, update

from ..db import owned, transaction
from ..integrations.mail import send_mail
from ..models import Job, Meeting, Organization, now


class CancelledWork(ValueError):
    pass


def assert_claim(db, org, job_id, fence):
    job = db.scalar(select(Job).where(Job.org_id == org, Job.id == job_id).with_for_update())
    if not job or job.state != "running" or job.fence != fence or job.lease_until < now():
        raise ValueError("stale worker claim")
    return job


def claim(factory, org, job_id):
    with transaction(factory, org) as db:
        row = db.execute(
            update(Job)
            .where(
                Job.org_id == org,
                Job.id == job_id,
                Job.next_at <= now(),
                or_(
                    Job.state.in_(["pending", "retry_wait"]),
                    (Job.state == "running") & (Job.lease_until < now()),
                ),
            )
            .values(
                state="running",
                fence=Job.fence + 1,
                attempts=Job.attempts + 1,
                lease_until=now() + 1800,
            )
            .returning(Job.fence)
        ).first()
        return row[0] if row else None


def execute(settings, factory, org, job_id):
    fence = claim(factory, org, job_id)
    if fence is None:
        return
    try:
        with transaction(factory, org) as db:
            job = assert_claim(db, org, job_id, fence)
            kind, payload, meeting_id = job.kind, job.input_json, job.meeting_id
        if kind == "pipeline":
            from .pipeline import process

            process(settings, factory, org, job_id, fence, payload, meeting_id)
        elif kind == "delivery":
            from .delivery import deliver

            deliver(settings, factory, org, job_id, fence, payload)
        elif kind == "zoom":
            from .zoom_source import collect

            collect(settings, factory, org, job_id, fence, payload, meeting_id)
        elif kind == "mail":
            send_mail(settings, payload["email"], payload["subject"], payload["body"])
        with transaction(factory, org) as db:
            job = owned(db, Job, org, id=job_id)
            if job.fence == fence and job.state == "running":
                job.state = "done"
    except Exception as exc:
        import httpx

        from .zoom_source import SourceNotReady

        transient = isinstance(
            exc, (SourceNotReady, httpx.TimeoutException, httpx.ConnectError)
        ) or (
            isinstance(exc, httpx.HTTPStatusError)
            and exc.response.status_code in {429, 500, 502, 503, 504}
        )
        with transaction(factory, org) as db:
            job = owned(db, Job, org, id=job_id)
            if not job or job.fence != fence:
                return
            job.state = (
                "cancelled"
                if isinstance(exc, CancelledWork)
                else "retry_wait"
                if transient and job.attempts < 8
                else "failed"
            )
            job.next_at = now() + min(300, 2**job.attempts * 10)
            if meeting_id and kind in {"pipeline", "zoom"}:
                meeting = owned(db, Meeting, org, id=meeting_id)
                if meeting and not meeting.deleted:
                    meeting.status = "failed"
            # Store only error class; never token-bearing exception strings.
            job.input_json = {**job.input_json, "error": type(exc).__name__}


def pending(factory):
    with factory() as global_db:
        orgs = list(global_db.scalars(select(Organization.id)))
    for org in orgs:
        with transaction(factory, org) as db:
            ids = list(
                db.scalars(
                    select(Job.id)
                    .where(
                        Job.org_id == org,
                        Job.next_at <= now(),
                        or_(
                            Job.state.in_(["pending", "retry_wait"]),
                            (Job.state == "running") & (Job.lease_until < now()),
                        ),
                    )
                    .limit(100)
                )
            )
        for job_id in ids:
            yield org, job_id


def run_pending(settings, factory):
    if settings.environment != "test":
        raise ValueError("inline runner is test-only; use Celery workers")
    for org, job_id in list(pending(factory)):
        execute(settings, factory, org, job_id)
