from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).timestamp()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[float]


class Token(Base):
    __tablename__ = "one_time_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(254), default="")
    org_id: Mapped[str | None] = mapped_column(String(36))
    purpose: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[float]


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    settings: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "auto_send": False,
            "policy_version": 1,
            "retention_days": 90,
            "audio_retention_days": 7,
            "audit_retention_days": 180,
            "monthly_meetings": 100,
        },
    )


class Membership(Base):
    __tablename__ = "memberships"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class Tenant:
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"
    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    external_account: Mapped[str] = mapped_column(String(100), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    # Directory contains routing IDs only, never credentials.
    external_users: Mapped[dict] = mapped_column(JSON, default=dict)


class Integration(Tenant, Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("org_id", "provider", "user_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(20))
    external_account: Mapped[str] = mapped_column(String(100))
    external_user: Mapped[str] = mapped_column(String(100))
    secret: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="connected")


class Meeting(Tenant, Base):
    __tablename__ = "meetings"
    __table_args__ = (UniqueConstraint("org_id", "id"), UniqueConstraint("org_id", "external_id"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(200))
    external_id: Mapped[str | None] = mapped_column(String(200))
    host_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), default="waiting_source")
    start_at: Mapped[str] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Seoul")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    generation: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(default=now)


class Recipient(Tenant, Base):
    __tablename__ = "recipients"
    __table_args__ = (
        ForeignKeyConstraint(["org_id", "meeting_id"], ["meetings.org_id", "meetings.id"]),
        ForeignKeyConstraint(["org_id", "user_id"], ["memberships.org_id", "memberships.user_id"]),
        UniqueConstraint("org_id", "meeting_id", "user_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(String(36))
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    kakao_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Transcript(Tenant, Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        ForeignKeyConstraint(["org_id", "meeting_id"], ["meetings.org_id", "meetings.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str] = mapped_column(String(36), unique=True)
    segments: Mapped[list] = mapped_column(JSON, default=list)
    source_key: Mapped[str] = mapped_column(Text, default="")


class Minutes(Tenant, Base):
    __tablename__ = "minutes"
    __table_args__ = (
        ForeignKeyConstraint(["org_id", "meeting_id"], ["meetings.org_id", "meetings.id"]),
        UniqueConstraint("org_id", "meeting_id", "version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    pdf_key: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class Approval(Tenant, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "meeting_id", "version"],
            ["minutes.org_id", "minutes.meeting_id", "minutes.version"],
        ),
        UniqueConstraint("org_id", "meeting_id", "version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30), default="human")
    policy_version: Mapped[int] = mapped_column(Integer, default=0)
    checks: Mapped[dict] = mapped_column(JSON, default=dict)


class Delivery(Tenant, Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "meeting_id", "version"],
            ["minutes.org_id", "minutes.meeting_id", "minutes.version"],
        ),
        ForeignKeyConstraint(["org_id", "user_id"], ["memberships.org_id", "memberships.user_id"]),
        UniqueConstraint("org_id", "meeting_id", "version", "user_id", "channel"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[str] = mapped_column(String(36))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    provider_id: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(String(100), default="")


class Job(Tenant, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("org_id", "dedupe_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meeting_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(250))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    fence: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[float] = mapped_column(default=0)
    next_at: Mapped[float] = mapped_column(default=now)


class WebhookReceipt(Base):
    __tablename__ = "webhook_receipts"
    dedupe_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    received_at: Mapped[float] = mapped_column(default=now)


class Audit(Tenant, Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[float] = mapped_column(default=now)


class Usage(Tenant, Base):
    __tablename__ = "usage"
    period: Mapped[str] = mapped_column(String(7), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    stt_seconds: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    meetings: Mapped[int] = mapped_column(Integer, default=0)
