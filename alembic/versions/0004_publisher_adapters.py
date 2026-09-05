"""Phase 4 idempotent publishing deliveries."""
from alembic import op
import sqlalchemy as sa

revision = "0004_publisher_adapters"
down_revision = "0003_review_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "publish_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_slot_id", sa.Integer(), sa.ForeignKey("schedule_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("external_post_id", sa.String(255), nullable=True),
        sa.Column("external_url", sa.String(2048), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("schedule_slot_id", name="uq_publish_deliveries_schedule_slot_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_publish_deliveries_idempotency_key"),
        sa.CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_publish_deliveries_status"),
    )
    op.create_index("ix_publish_deliveries_schedule_slot_id", "publish_deliveries", ["schedule_slot_id"])


def downgrade():
    op.drop_index("ix_publish_deliveries_schedule_slot_id", table_name="publish_deliveries")
    op.drop_table("publish_deliveries")
