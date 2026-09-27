"""Move attorney credentials to Supabase Auth and lock tables away from the Data API.

- users.id is now the Supabase Auth user id; the password hash column goes away.
- Row level security is enabled on every table with no policies, and the Supabase API roles
  lose their grants, so Supabase's auto-generated REST/GraphQL APIs can't read lead data
  with the publishable key. The backend connects as the table owner, which RLS doesn't
  restrict. On plain Postgres (tests, CI) the Supabase roles don't exist and are skipped.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("users", "leads", "email_outbox", "alembic_version")

REVOKE_SUPABASE_ROLES = """
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format('REVOKE ALL ON TABLE %s FROM %I', '{table}', api_role);
        END IF;
    END LOOP;
END
$$;
"""


def upgrade() -> None:
    # Existing local accounts had app-managed passwords that don't exist in Supabase Auth;
    # they can't be carried over, so start from a clean attorney list.
    op.execute("DELETE FROM users")
    op.drop_column("users", "hashed_password")

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(REVOKE_SUPABASE_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("users", "hashed_password", server_default=None)
