"""private invitations and revocable account access"""

import sqlalchemy as sa
from alembic import op

revision = "0003_household_invitations"
down_revision = "0002_household_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "household_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("private_nonce", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("role IN ('editor','viewer')", name="ck_invitation_role"),
        sa.CheckConstraint("version >= 1", name="ck_invitation_version"),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
        ),
        sa.ForeignKeyConstraint(
            ["member_id", "household_id"],
            ["household_members.id", "household_members.household_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_household_invitations_household_id"),
        "household_invitations",
        ["household_id"],
        unique=False,
    )
    op.add_column(
        "household_members",
        sa.Column("access_enabled", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "household_members",
        sa.Column("access_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("household_members", "access_version")
    op.drop_column("household_members", "access_enabled")
    op.drop_index(op.f("ix_household_invitations_household_id"), table_name="household_invitations")
    op.drop_table("household_invitations")
