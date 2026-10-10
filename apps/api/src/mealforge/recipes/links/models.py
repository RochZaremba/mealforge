from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mealforge.core.database import Base


class RecipeLink(Base):
    __tablename__ = "recipe_links"
    __table_args__ = (
        UniqueConstraint("household_id", "canonical_url", name="uq_recipe_link_canonical"),
        CheckConstraint("octet_length(source_url) <= 2048", name="ck_link_source_url_size"),
        CheckConstraint("octet_length(canonical_url) <= 2048", name="ck_link_canonical_url_size"),
        CheckConstraint("status = 'link_only'", name="ck_link_status"),
        CheckConstraint("version = 1", name="ck_link_version"),
        CheckConstraint(
            "NOT planner_eligible AND NOT automatic_fetch_enabled", name="ck_link_no_execution"
        ),
        CheckConstraint("license IS NULL", name="ck_link_unknown_license"),
        CheckConstraint(
            "own_contribution_attestation = 'i_am_author_of_label_and_note'",
            name="ck_link_attestation",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id"), index=True)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    host: Mapped[str] = mapped_column(String(253))
    source_id: Mapped[str | None] = mapped_column(String(64))
    source_registry_checked_at: Mapped[date]
    user_title: Mapped[str] = mapped_column(String(160))
    own_note: Mapped[str | None] = mapped_column(String(2000))
    own_contribution_attestation: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(12), default="link_only", server_default="link_only")
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    planner_eligible: Mapped[bool] = mapped_column(default=False, server_default="false")
    automatic_fetch_enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    license: Mapped[str | None] = mapped_column(String(64), default=None)
