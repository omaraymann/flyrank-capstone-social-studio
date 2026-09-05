"""Phase 6 LLM generation audit records."""

from alembic import op
import sqlalchemy as sa

revision = "0006_llm_generation"
down_revision = "0005_durable_worker"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_post_id", sa.Integer(), sa.ForeignKey("source_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(150), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("examples_version", sa.String(50), nullable=False),
        sa.Column("platforms", sa.String(100), nullable=False),
        sa.Column("audience", sa.String(300), nullable=False),
        sa.Column("goal", sa.String(50), nullable=False),
        sa.Column("tone", sa.String(50), nullable=False),
        sa.Column("call_to_action", sa.String(500), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("top_p", sa.Float(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("repair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="processing"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_generation_runs_status"),
    )
    op.create_index("ix_generation_runs_source_post_id", "generation_runs", ["source_post_id"])


def downgrade():
    op.drop_index("ix_generation_runs_source_post_id", table_name="generation_runs")
    op.drop_table("generation_runs")
