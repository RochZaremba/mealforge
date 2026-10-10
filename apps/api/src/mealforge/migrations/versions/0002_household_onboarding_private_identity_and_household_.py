"""private identity and household onboarding"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_household_onboarding"
down_revision = "0001_reference_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_buckets",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column("window", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("bucket_key", "window"),
    )
    op.create_index(
        op.f("ix_auth_rate_buckets_expires_at"), "auth_rate_buckets", ["expires_at"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "households",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("slot_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=48), nullable=False),
        sa.Column("key", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_user_id", "scope", "key"),
    )
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("version_before", sa.Integer(), nullable=True),
        sa.Column("version_after", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "household_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("is_guest", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("target_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("role IN ('owner','editor','viewer')", name="ck_member_role"),
        sa.CheckConstraint("NOT is_guest OR user_id IS NULL", name="ck_guest_no_login"),
        sa.CheckConstraint("target_revision >= 0", name="ck_target_revision"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "user_id"),
        sa.UniqueConstraint("id", "household_id"),
    )
    op.create_table(
        "meal_slot_presets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column("default_time", sa.Time(), nullable=True),
        sa.Column("default_share", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("repeat_weekly", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "default_share IS NULL OR (default_share >= 0 AND default_share <= 1)",
            name="ck_slot_share",
        ),
        sa.CheckConstraint("ordering >= 0", name="ck_slot_order"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "nutrition_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kcal_target", sa.Numeric(precision=9, scale=3), nullable=True),
        sa.Column("protein_target_g", sa.Numeric(precision=9, scale=3), nullable=True),
        sa.Column("carbs_target_g", sa.Numeric(precision=9, scale=3), nullable=True),
        sa.Column("fat_target_g", sa.Numeric(precision=9, scale=3), nullable=True),
        sa.Column("goal_type", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("carbs_target_g IS NULL OR carbs_target_g >= 0", name="ck_target_carbs"),
        sa.CheckConstraint("fat_target_g IS NULL OR fat_target_g >= 0", name="ck_target_fat"),
        sa.CheckConstraint("kcal_target IS NULL OR kcal_target > 0", name="ck_target_energy"),
        sa.CheckConstraint(
            "protein_target_g IS NULL OR protein_target_g >= 0", name="ck_target_protein"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
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
        sa.UniqueConstraint("member_id", "version"),
    )
    op.execute("""
        CREATE FUNCTION mealforge_reject_history_update() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'History records are immutable' USING ERRCODE = '23514';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER nutrition_history_immutable BEFORE UPDATE OR DELETE ON nutrition_profiles
        FOR EACH ROW EXECUTE FUNCTION mealforge_reject_history_update()
    """)
    op.execute("""
        CREATE TRIGGER audit_history_immutable BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION mealforge_reject_history_update()
    """)


def downgrade() -> None:
    op.drop_table("nutrition_profiles")
    op.drop_table("meal_slot_presets")
    op.drop_table("household_members")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("idempotency_records")
    op.drop_table("households")
    op.drop_table("users")
    op.drop_index(op.f("ix_auth_rate_buckets_expires_at"), table_name="auth_rate_buckets")
    op.drop_table("auth_rate_buckets")
    op.execute("DROP FUNCTION mealforge_reject_history_update()")
