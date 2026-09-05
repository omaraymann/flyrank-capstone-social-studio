"""Phase 5 durable worker leases, retries, and attempt history."""
from alembic import op
import sqlalchemy as sa

revision = "0005_durable_worker"
down_revision = "0004_publisher_adapters"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("schedule_slots", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schedule_slots", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schedule_slots", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("schedule_slots", sa.Column("worker_id", sa.String(100), nullable=True))
    op.add_column("schedule_slots", sa.Column("last_error", sa.Text(), nullable=True))
    op.create_index("ix_schedule_slots_next_attempt_at", "schedule_slots", ["next_attempt_at"])
    op.create_index("ix_schedule_slots_lease_expires_at", "schedule_slots", ["lease_expires_at"])
    op.create_table(
        "publish_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("delivery_id", sa.Integer(), sa.ForeignKey("publish_deliveries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("delivery_id", "attempt_number", name="uq_publish_attempt_number"),
        sa.CheckConstraint(
            "status IN ('processing', 'succeeded', 'failed', 'uncertain')",
            name="ck_publish_attempts_status",
        ),
    )
    op.create_index("ix_publish_attempts_delivery_id", "publish_attempts", ["delivery_id"])


def downgrade():
    op.drop_index("ix_publish_attempts_delivery_id", table_name="publish_attempts")
    op.drop_table("publish_attempts")
    op.drop_index("ix_schedule_slots_lease_expires_at", table_name="schedule_slots")
    op.drop_index("ix_schedule_slots_next_attempt_at", table_name="schedule_slots")
    op.drop_column("schedule_slots", "last_error")
    op.drop_column("schedule_slots", "worker_id")
    op.drop_column("schedule_slots", "lease_expires_at")
    op.drop_column("schedule_slots", "claimed_at")
    op.drop_column("schedule_slots", "next_attempt_at")
