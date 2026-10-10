from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from mealforge.core.database import Base


class MealSlotDefinition(Base):
    __tablename__ = "meal_slot_definitions"
    __table_args__ = (CheckConstraint("position >= 0", name="ck_meal_slot_position"),)

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False, unique=True)
