"""Private immutable link-only source bookmarks; no network work."""

import sqlalchemy as sa
from alembic import op

revision = "0005_recipe_links"
down_revision = "0004_private_recipes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipe_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("host", sa.String(253), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
        sa.Column("source_registry_checked_at", sa.Date(), nullable=False),
        sa.Column("user_title", sa.String(160), nullable=False),
        sa.Column("own_note", sa.String(2000), nullable=True),
        sa.Column("own_contribution_attestation", sa.String(40), nullable=False),
        sa.Column("status", sa.String(12), server_default="link_only", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("planner_eligible", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("automatic_fetch_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("license", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.UniqueConstraint("household_id", "canonical_url", name="uq_recipe_link_canonical"),
        sa.CheckConstraint("octet_length(source_url) <= 2048", name="ck_link_source_url_size"),
        sa.CheckConstraint(
            "octet_length(canonical_url) <= 2048", name="ck_link_canonical_url_size"
        ),
        sa.CheckConstraint("status = 'link_only'", name="ck_link_status"),
        sa.CheckConstraint("version = 1", name="ck_link_version"),
        sa.CheckConstraint(
            "NOT planner_eligible AND NOT automatic_fetch_enabled", name="ck_link_no_execution"
        ),
        sa.CheckConstraint("license IS NULL", name="ck_link_unknown_license"),
        sa.CheckConstraint(
            "own_contribution_attestation = 'i_am_author_of_label_and_note'",
            name="ck_link_attestation",
        ),
    )
    op.create_index("ix_recipe_links_household_id", "recipe_links", ["household_id"])
    op.execute(
        "CREATE TRIGGER recipe_links_immutable BEFORE UPDATE OR DELETE ON recipe_links "
        "FOR EACH ROW EXECUTE FUNCTION mealforge_reject_history_update()"
    )


def downgrade() -> None:
    op.drop_index("ix_recipe_links_household_id", table_name="recipe_links")
    op.drop_table("recipe_links")
