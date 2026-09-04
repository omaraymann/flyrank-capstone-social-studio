"""Phase 3 review workflow and schedule slots."""
from alembic import op
import sqlalchemy as sa

revision = "0003_review_workflow"
down_revision = "0002_posts_and_variants"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("platform_variants", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("platform_variants", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "platform_variants",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint(
        "ck_platform_variants_status",
        "platform_variants",
        "status IN ('draft', 'approved', 'rejected', 'scheduled', 'published')",
    )
    op.create_table(
        "schedule_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("platform_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("variant_id", name="uq_schedule_slots_variant_id"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_schedule_slots_status"),
    )
    op.create_index("ix_schedule_slots_variant_id", "schedule_slots", ["variant_id"])
    op.create_index("ix_schedule_slots_publish_at", "schedule_slots", ["publish_at"])


def downgrade():
    op.drop_index("ix_schedule_slots_publish_at", table_name="schedule_slots")
    op.drop_index("ix_schedule_slots_variant_id", table_name="schedule_slots")
    op.drop_table("schedule_slots")
    op.drop_constraint("ck_platform_variants_status", "platform_variants", type_="check")
    op.drop_column("platform_variants", "updated_at")
    op.drop_column("platform_variants", "reviewed_at")
    op.drop_column("platform_variants", "rejection_reason")
