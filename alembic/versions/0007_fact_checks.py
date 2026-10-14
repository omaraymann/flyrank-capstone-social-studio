"""Persistent on-demand factuality checks with source and draft snapshots."""
from alembic import op
import sqlalchemy as sa
revision = "0007_fact_checks"
down_revision = "0006_llm_generation"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("fact_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("platform_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_snapshot", sa.Text(), nullable=False),
        sa.Column("source_snapshot", sa.Text(), nullable=False),
        sa.Column("draft_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("extraction_model", sa.String(150), nullable=False),
        sa.Column("audit_model", sa.String(150), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_fact_checks_status"))
    op.create_index("ix_fact_checks_variant_id", "fact_checks", ["variant_id"])
    op.create_index("uq_fact_checks_processing_variant", "fact_checks", ["variant_id"], unique=True,
        sqlite_where=sa.text("status = 'processing'"), postgresql_where=sa.text("status = 'processing'"))

def downgrade():
    op.drop_index("uq_fact_checks_processing_variant", table_name="fact_checks")
    op.drop_index("ix_fact_checks_variant_id", table_name="fact_checks")
    op.drop_table("fact_checks")
