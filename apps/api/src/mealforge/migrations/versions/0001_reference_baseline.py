"""Non-private reference baseline. No households or invented nutrient records."""

import sqlalchemy as sa
from alembic import op

revision = "0001_reference_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meal_slot_definitions",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_meal_slot_position"),
        sa.UniqueConstraint("position"),
    )


def downgrade() -> None:
    op.drop_table("meal_slot_definitions")
