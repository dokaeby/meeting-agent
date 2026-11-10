from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Register(Input):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=200)


class Reset(Input):
    email: EmailStr


class ResetConfirm(TokenInput):
    password: str = Field(min_length=12, max_length=128)


class OrgInput(Input):
    name: str = Field(min_length=1, max_length=100)


class Invite(Input):
    email: EmailStr
    role: Literal["admin", "manager", "member"] = "member"


class MemberUpdate(Input):
    role: Literal["admin", "manager", "member"]
    active: bool
    aliases: list[str] = Field(default_factory=list, max_length=20)


class Policy(Input):
    auto_send: bool = False
    retention_days: int = Field(default=90, ge=1, le=90)
    audio_retention_days: int = Field(default=7, ge=1, le=7)
    audit_retention_days: int = Field(default=180, ge=1, le=180)
    monthly_meetings: int = Field(default=100, ge=1, le=1000)
    ai_consent: bool = False


class MeetingInput(Input):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    timezone: str = "Asia/Seoul"

    @field_validator("start_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("timezone-aware start_at required")
        return value

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("invalid IANA timezone") from exc
        return value


class RecipientInput(Input):
    user_id: str
    email: bool = True
    kakao: bool = False


class VersionInput(Input):
    version: int = Field(ge=1)


class Evidence(Input):
    text: str = Field(min_length=1, max_length=12000)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)


class Action(Evidence):
    assignee_id: str | None = None
    assignee_name: str | None = None
    due_raw: str | None = None
    due_at: datetime | None = None

    @field_validator("due_at")
    @classmethod
    def aware(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("timezone-aware due_at required")
        return value


class Summary(Input):
    title: str = Field(min_length=1, max_length=200)
    overview: Evidence
    discussions: list[Evidence] = Field(default_factory=list, max_length=100)
    decisions: list[Evidence] = Field(default_factory=list, max_length=100)
    actions: list[Action] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)


class MinutesEdit(Input):
    expected_version: int = Field(ge=1)
    content: Summary


class RetryInput(Input):
    acknowledge_duplicate_risk: bool = False
