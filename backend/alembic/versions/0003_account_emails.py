"""Queue attorney invite and password-reset emails in the outbox.

- email_outbox rows can now belong to an attorney account (user_id) instead of a lead;
  exactly one of lead_id / user_id is set.
- email_kind gains ATTORNEY_INVITE and PASSWORD_RESET.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New enum values can't be used in the transaction that adds them; nothing here does.
    op.execute("ALTER TYPE email_kind ADD VALUE IF NOT EXISTS 'ATTORNEY_INVITE'")
    op.execute("ALTER TYPE email_kind ADD VALUE IF NOT EXISTS 'PASSWORD_RESET'")

    op.add_column(
        "email_outbox",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", name="fk_email_outbox_user_id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_email_outbox_user_id", "email_outbox", ["user_id"])
    op.alter_column("email_outbox", "lead_id", nullable=True)
    op.create_check_constraint(
        "ck_email_outbox_one_subject", "email_outbox", "num_nonnulls(lead_id, user_id) = 1"
    )


def downgrade() -> None:
    op.execute("DELETE FROM email_outbox WHERE user_id IS NOT NULL")
    op.drop_constraint("ck_email_outbox_one_subject", "email_outbox", type_="check")
    op.alter_column("email_outbox", "lead_id", nullable=False)
    op.drop_index("ix_email_outbox_user_id", table_name="email_outbox")
    op.drop_column("email_outbox", "user_id")

    # Postgres can't drop enum values, so rebuild the type without them.
    op.execute("ALTER TYPE email_kind RENAME TO email_kind_old")
    op.execute("CREATE TYPE email_kind AS ENUM ('PROSPECT_CONFIRMATION', 'ATTORNEY_NOTIFICATION')")
    op.execute(
        "ALTER TABLE email_outbox ALTER COLUMN kind TYPE email_kind USING kind::text::email_kind"
    )
    op.execute("DROP TYPE email_kind_old")
