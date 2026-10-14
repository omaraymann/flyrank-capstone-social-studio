"""Persist RAG evidence used by campaign generation."""
from alembic import op
import sqlalchemy as sa

revision = "0009_rag_generation_audit"
down_revision = "0008_fix_suggestions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generation_runs", sa.Column("rag_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("generation_runs", sa.Column("rag_top_k", sa.Integer(), nullable=True))
    op.add_column("generation_runs", sa.Column("rag_model_id", sa.String(length=200), nullable=True))
    op.add_column("generation_runs", sa.Column("rag_context", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("generation_runs", "rag_context")
    op.drop_column("generation_runs", "rag_model_id")
    op.drop_column("generation_runs", "rag_top_k")
    op.drop_column("generation_runs", "rag_enabled")
