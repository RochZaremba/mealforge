"""Deduplicate exact private own JSON-LD imports without rewriting immutable history."""

import sqlalchemy as sa
from alembic import op

revision = "0006_jsonld_origin_dedup"
down_revision = "0005_recipe_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_recipe_import_source",
        "recipe_versions",
        [
            "household_id",
            sa.text("(snapshot #>> '{provenance,import_origin,source_sha256}'::text[])"),
        ],
        unique=True,
        postgresql_where=sa.text(
            "version = 1 AND "
            "(snapshot #>> '{provenance,import_origin,source_sha256}'::text[]) IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_recipe_import_source", table_name="recipe_versions")
