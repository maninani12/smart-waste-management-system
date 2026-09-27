"""Add optional email outbox without altering existing records."""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.String(100), nullable=False),
    )
    op.create_index("ix_notification_deliveries_status", "notification_deliveries", ["status"])


def downgrade():
    raise RuntimeError("Destructive downgrade is disabled. Restore a verified backup.")
