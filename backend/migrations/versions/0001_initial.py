"""Initial schema and tenant row security."""

from alembic import op
import sqlalchemy as sa
from meeting_agent.models import Base, Tenant

revision = "0001"
down_revision = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    bind.execute(
        sa.text(
            "INSERT INTO organizations (id,name,settings) VALUES ('system','system','{}') ON CONFLICT (id) DO NOTHING"
        )
    )
    if bind.dialect.name == "postgresql":
        for mapper in Base.registry.mappers:
            model = mapper.class_
            if issubclass(model, Tenant):
                table = model.__tablename__
                op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
                op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
                op.execute(f"""CREATE POLICY tenant_isolation ON "{table}"
                    USING (org_id=current_setting('app.org_id',true))
                    WITH CHECK (org_id=current_setting('app.org_id',true))""")


def downgrade():
    raise RuntimeError("Destructive downgrade requires an approved recovery plan")
