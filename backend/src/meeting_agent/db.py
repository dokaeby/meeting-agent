from contextlib import contextmanager

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from .models import Tenant


def make_database(url: str):
    args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=args, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Session, "do_orm_execute")
def tenant_filter(state):
    org = state.session.info.get("org")
    if org and state.is_select:
        state.statement = state.statement.options(
            with_loader_criteria(Tenant, lambda model: model.org_id == org, include_aliases=True)
        )


def set_tenant(db: Session, org: str):
    db.info["org"] = org
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.org_id', :org, true)"), {"org": org})


@event.listens_for(Session, "after_begin")
def restore_tenant(db, transaction, connection):
    if connection.dialect.name == "postgresql" and db.info.get("org"):
        connection.execute(
            text("SELECT set_config('app.org_id', :org, true)"), {"org": db.info["org"]}
        )


@contextmanager
def transaction(factory, org=None):
    with factory() as db:
        if org:
            set_tenant(db, org)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def owned(db: Session, model, org: str, **where):
    return db.scalar(select(model).filter_by(org_id=org, **where))
