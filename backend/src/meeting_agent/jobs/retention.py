from sqlalchemy import delete, select

from ..db import transaction
from ..models import (
    Approval,
    Audit,
    Delivery,
    Job,
    Meeting,
    Minutes,
    Organization,
    Recipient,
    Transcript,
    now,
)
from ..storage import path_for


def cleanup(settings, factory):
    with factory() as db:
        companies = [(c.id, c.settings) for c in db.scalars(select(Organization))]
    for org, policy in companies:
        with transaction(factory, org) as db:
            meetings = list(db.scalars(select(Meeting).where(Meeting.org_id == org)))
            for meeting in meetings:
                age_days = (now() - meeting.created_at) / 86400
                full_delete = meeting.deleted or age_days > policy.get("retention_days", 90)
                directory = path_for(settings, f"{org}/{meeting.id}")
                # Only generated files under the verified private meeting directory.
                if directory.is_dir():
                    for file in directory.iterdir():
                        if file.is_file() and (
                            full_delete
                            or (
                                file.suffix.lower() in {".mp3", ".m4a", ".wav"}
                                and age_days > policy.get("audio_retention_days", 7)
                            )
                        ):
                            file.unlink(missing_ok=True)
                if full_delete:
                    meeting.deleted = True
                    meeting.generation += 1
                    for model in (Delivery, Approval, Minutes, Transcript, Recipient, Job):
                        db.execute(
                            delete(model).where(model.org_id == org, model.meeting_id == meeting.id)
                        )
                    meeting.title = "[삭제된 회의]"
            db.execute(
                delete(Audit).where(
                    Audit.org_id == org,
                    Audit.created_at < now() - policy.get("audit_retention_days", 180) * 86400,
                )
            )
