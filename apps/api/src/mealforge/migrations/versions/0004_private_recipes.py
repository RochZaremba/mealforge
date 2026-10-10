"""Private immutable recipe snapshots and separately confirmed demonstration."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_private_recipes"
down_revision = "0003_household_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "households",
        sa.Column("source", sa.String(16), server_default="user_created", nullable=False),
    )
    op.create_check_constraint(
        "ck_household_source", "households", "source IN ('user_created','demo_seed')"
    )
    op.create_table(
        "recipes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "household_id"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.CheckConstraint("current_version >= 1", name="ck_recipe_current_version"),
    )
    op.create_index("ix_recipes_household_id", "recipes", ["household_id"])
    op.create_table(
        "recipe_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "household_id", "version"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["recipe_id", "household_id"],
            ["recipes.id", "recipes.household_id"],
            name="fk_recipe_version_identity",
        ),
        sa.CheckConstraint("version >= 1", name="ck_recipe_version"),
        sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_recipe_snapshot_object"),
        sa.CheckConstraint("octet_length(snapshot::text) <= 32768", name="ck_recipe_snapshot_size"),
    )
    op.create_foreign_key(
        "fk_recipe_current_version",
        "recipes",
        "recipe_versions",
        ["id", "household_id", "current_version"],
        ["recipe_id", "household_id", "version"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute(
        "CREATE TRIGGER recipe_versions_immutable BEFORE UPDATE OR DELETE ON recipe_versions "
        "FOR EACH ROW EXECUTE FUNCTION mealforge_reject_history_update()"
    )


def downgrade() -> None:
    op.drop_constraint("fk_recipe_current_version", "recipes", type_="foreignkey")
    op.drop_table("recipe_versions")
    op.drop_index("ix_recipes_household_id", table_name="recipes")
    op.drop_table("recipes")
    op.drop_constraint("ck_household_source", "households", type_="check")
    op.drop_column("households", "source")
