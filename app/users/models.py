from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.mixins import IDMixin
from app.core.database.sqlalchemy_base import BaseModel


class TelegramUserModel(IDMixin, BaseModel):
    __tablename__ = "telegram_user"

    __table_args__ = (
        CheckConstraint("win_count >= 0", name="win_count_non_negative"),
        CheckConstraint("loss_count >= 0", name="loss_count_non_negative"),
    )

    username: Mapped[str] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(default=0)
    win_count: Mapped[int] = mapped_column(default=0)
    loss_count: Mapped[int] = mapped_column(default=0)
