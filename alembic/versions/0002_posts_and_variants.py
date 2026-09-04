"""Phase 2 source posts and platform variants."""
from alembic import op
import sqlalchemy as sa

revision = "0002_posts_and_variants"
down_revision = "0001_phase_one"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_posts_owner_id", "source_posts", ["owner_id"])
    op.create_table(
        "platform_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_post_id", sa.Integer(), sa.ForeignKey("source_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_post_id", "platform", name="uq_source_platform"),
    )


def downgrade():
    op.drop_table("platform_variants")
    op.drop_index("ix_source_posts_owner_id", table_name="source_posts")
    op.drop_table("source_posts")
