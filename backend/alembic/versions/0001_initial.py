"""Create users, leads and email_outbox.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

lead_state = sa.Enum("PENDING", "REACHED_OUT", name="lead_state")
email_kind = sa.Enum("PROSPECT_CONFIRMATION", "ATTORNEY_NOTIFICATION", name="email_kind")
email_status = sa.Enum("PENDING", "SENT", "FAILED", name="email_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("resume_object_key", sa.String(length=512), nullable=False),
        sa.Column("resume_filename", sa.String(length=255), nullable=False),
        sa.Column("resume_content_type", sa.String(length=100), nullable=False),
        sa.Column("resume_size_bytes", sa.Integer(), nullable=False),
        sa.Column("state", lead_state, server_default="PENDING", nullable=False),
        sa.Column("reached_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reached_out_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reached_out_by_id"],
            ["users.id"],
            name=op.f("fk_leads_reached_out_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index("ix_leads_state_created_at", "leads", ["state", "created_at"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index("ix_leads_email", "leads", ["email"])

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("kind", email_kind, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("status", email_status, server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name=op.f("fk_email_outbox_lead_id_leads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_outbox")),
    )
    op.create_index(
        "ix_email_outbox_status_next_attempt_at", "email_outbox", ["status", "next_attempt_at"]
    )
    op.create_index(op.f("ix_email_outbox_lead_id"), "email_outbox", ["lead_id"])


def downgrade() -> None:
    op.drop_table("email_outbox")
    op.drop_table("leads")
    op.drop_table("users")
    email_status.drop(op.get_bind(), checkfirst=True)
    email_kind.drop(op.get_bind(), checkfirst=True)
    lead_state.drop(op.get_bind(), checkfirst=True)
