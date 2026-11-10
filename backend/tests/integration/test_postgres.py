import os
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from meeting_agent.db import make_database, transaction
from meeting_agent.models import Meeting

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg():
    url = os.environ.get("PG_TEST_URL")
    if not url:
        pytest.skip("PG_TEST_URL runtime-role database not available")
    engine, factory = make_database(url)
    yield engine, factory
    engine.dispose()


def test_runtime_role_and_rls_default_deny(pg):
    engine, factory = pg
    with engine.connect() as connection:
        info = connection.execute(
            text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        ).one()
        assert not info.rolsuper and not info.rolbypassrls
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner=current_user"
                )
            ).scalar()
            == 0
        )
        assert connection.execute(text("SELECT count(*) FROM meetings")).scalar() == 0
    with transaction(factory, str(uuid4())) as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "INSERT INTO meetings (id,org_id,title,status,start_at,timezone,deleted,generation,created_at) VALUES (:id,:org,'forbidden','waiting_source','2026-11-10','UTC',false,0,0)"
                ),
                {"id": str(uuid4()), "org": str(uuid4())},
            )


def test_tenant_context_does_not_escape_transaction(pg):
    engine, factory = pg
    with transaction(factory, "nonexistent-tenant") as db:
        assert list(db.scalars(select(Meeting))) == []
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_setting('app.org_id',true)")).scalar() in (
            None,
            "",
        )
