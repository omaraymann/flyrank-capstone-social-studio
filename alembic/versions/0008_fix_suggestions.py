"""Reviewed AI fix suggestions and explicit recheck requirement after applying."""
from alembic import op
import sqlalchemy as sa
revision = "0008_fix_suggestions"
down_revision = "0007_fact_checks"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("platform_variants", sa.Column("fact_recheck_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("revision_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("platform_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fact_check_id", sa.Integer(), sa.ForeignKey("fact_checks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_snapshot", sa.Text(), nullable=False),
        sa.Column("draft_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("call_to_action", sa.String(500), nullable=True),
        sa.Column("suggested_content", sa.Text(), nullable=True),
        sa.Column("model", sa.String(150), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("reported_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_revision_suggestions_status"))
    op.create_index("ix_revision_suggestions_variant_id", "revision_suggestions", ["variant_id"])
    op.create_index("uq_revision_suggestions_processing_variant", "revision_suggestions", ["variant_id"], unique=True,
        sqlite_where=sa.text("status = 'processing'"), postgresql_where=sa.text("status = 'processing'"))

def downgrade():
    op.drop_index("uq_revision_suggestions_processing_variant", table_name="revision_suggestions")
    op.drop_index("ix_revision_suggestions_variant_id", table_name="revision_suggestions")
    op.drop_table("revision_suggestions")
    op.drop_column("platform_variants", "fact_recheck_required")
