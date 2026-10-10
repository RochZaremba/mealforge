from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mealforge.core.database import Base


class Household(Base):
    __tablename__ = "households"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80))
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    timezone: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    slot_revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (
        UniqueConstraint("household_id", "user_id"),
        UniqueConstraint("id", "household_id"),
        CheckConstraint("role IN ('owner','editor','viewer')", name="ck_member_role"),
        CheckConstraint("NOT is_guest OR user_id IS NULL", name="ck_guest_no_login"),
        CheckConstraint("target_revision >= 0", name="ck_target_revision"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(12))
    is_guest: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)
    target_revision: Mapped[int] = mapped_column(default=0)


class NutritionProfile(Base):
    __tablename__ = "nutrition_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["member_id", "household_id"],
            ["household_members.id", "household_members.household_id"],
        ),
        UniqueConstraint("member_id", "version"),
        CheckConstraint("kcal_target IS NULL OR kcal_target > 0", name="ck_target_energy"),
        CheckConstraint(
            "protein_target_g IS NULL OR protein_target_g >= 0", name="ck_target_protein"
        ),
        CheckConstraint("carbs_target_g IS NULL OR carbs_target_g >= 0", name="ck_target_carbs"),
        CheckConstraint("fat_target_g IS NULL OR fat_target_g >= 0", name="ck_target_fat"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id"))
    member_id: Mapped[UUID]
    version: Mapped[int]
    kcal_target: Mapped[Decimal | None] = mapped_column(Numeric(9, 3))
    protein_target_g: Mapped[Decimal | None] = mapped_column(Numeric(9, 3))
    carbs_target_g: Mapped[Decimal | None] = mapped_column(Numeric(9, 3))
    fat_target_g: Mapped[Decimal | None] = mapped_column(Numeric(9, 3))
    goal_type: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(16), default="user_set")
    valid_from: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class MealSlotPreset(Base):
    __tablename__ = "meal_slot_presets"
    __table_args__ = (
        CheckConstraint("ordering >= 0", name="ck_slot_order"),
        CheckConstraint(
            "default_share IS NULL OR (default_share >= 0 AND default_share <= 1)",
            name="ck_slot_share",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    ordering: Mapped[int]
    default_time: Mapped[time | None]
    default_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    repeat_weekly: Mapped[bool]
    active: Mapped[bool] = mapped_column(default=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id"))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(48))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[UUID]
    version_before: Mapped[int | None]
    version_after: Mapped[int | None]
    request_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor_user_id", "scope", "key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(48))
    key: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, object]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
