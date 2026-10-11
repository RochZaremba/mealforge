from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mealforge.core.database import Base


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("id", "household_id"),
        CheckConstraint("current_version >= 1", name="ck_recipe_current_version"),
        ForeignKeyConstraint(
            ["id", "household_id", "current_version"],
            [
                "recipe_versions.recipe_id",
                "recipe_versions.household_id",
                "recipe_versions.version",
            ],
            name="fk_recipe_current_version",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id"), index=True)
    current_version: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RecipeVersion(Base):
    __tablename__ = "recipe_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recipe_id", "household_id"],
            ["recipes.id", "recipes.household_id"],
            name="fk_recipe_version_identity",
        ),
        UniqueConstraint("recipe_id", "household_id", "version"),
        CheckConstraint("version >= 1", name="ck_recipe_version"),
        CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_recipe_snapshot_object"),
        CheckConstraint("octet_length(snapshot::text) <= 32768", name="ck_recipe_snapshot_size"),
        Index(
            "uq_recipe_import_source",
            "household_id",
            text("(snapshot #>> '{provenance,import_origin,source_sha256}'::text[])"),
            unique=True,
            postgresql_where=text(
                "version = 1 AND "
                "(snapshot #>> '{provenance,import_origin,source_sha256}'::text[]) IS NOT NULL"
            ),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipe_id: Mapped[UUID]
    household_id: Mapped[UUID] = mapped_column(ForeignKey("households.id"))
    version: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
