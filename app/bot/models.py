from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Enum as PgEnum,
    ForeignKey,
    Interval,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.mixins import IDMixin
from app.core.database.sqlalchemy_base import BaseModel


class GameStatusEnum(StrEnum):
    LOBBY = "lobby"
    ROUND_1 = "round_1"
    ROUND_2 = "round_2"
    ROUND_3 = "round_3"
    COMPLETED = "completed"


class RoundTypeEnum(StrEnum):
    ROUND_1 = "round_1"
    ROUND_2 = "round_2"
    ROUND_3 = "round_3"


class AnswerStatusEnum(StrEnum):
    NOT_ANSWERED = "not_answered"
    ANSWERED = "answered"
    WAIT_ANSWERED = "wait_answered"


class TelegramUserModel(BaseModel):
    __tablename__ = "telegram_user"

    __table_args__ = (
        CheckConstraint("win_count >= 0", name="win_count_non_negative"),
        CheckConstraint("loss_count >= 0", name="loss_count_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(default=0)
    win_count: Mapped[int] = mapped_column(default=0)
    loss_count: Mapped[int] = mapped_column(default=0)


class GameModel(IDMixin, BaseModel):
    __tablename__ = "game"

    chat_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[GameStatusEnum] = mapped_column(
        PgEnum(GameStatusEnum),
        default=GameStatusEnum.LOBBY,
    )
    master_id: Mapped[int] = mapped_column(ForeignKey("telegram_user.id"))
    active_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_user.id"),
        nullable=True,
    )
    choice_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_user.id"),
        nullable=True,
    )


class TelegramUserToGameModel(BaseModel):
    __tablename__ = "telegram_user_to_game"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_user.id"),
        primary_key=True,
    )
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"), primary_key=True)
    score: Mapped[int] = mapped_column(default=0)

    user: Mapped[TelegramUserModel] = relationship()


class RoundModel(IDMixin, BaseModel):
    __tablename__ = "round"

    type: Mapped[RoundTypeEnum] = mapped_column(PgEnum(RoundTypeEnum))

    @property
    def base_score(self):
        data = {
            RoundTypeEnum.ROUND_1: 100,
            RoundTypeEnum.ROUND_2: 200,
            RoundTypeEnum.ROUND_3: 300,
        }
        return data[self.type]


class ThemeModel(IDMixin, BaseModel):
    __tablename__ = "theme"

    title: Mapped[str] = mapped_column(String(255))
    questions: Mapped[list["QuestionModel"]] = relationship(
        back_populates="theme",
        cascade="all, delete-orphan",
    )


class QuestionModel(IDMixin, BaseModel):
    __tablename__ = "question"

    text: Mapped[str] = mapped_column(String(255))
    answer: Mapped[str] = mapped_column(String(255))
    hard_level: Mapped[int] = mapped_column(SmallInteger)
    theme_id: Mapped[int] = mapped_column(ForeignKey("theme.id"))

    theme: Mapped[ThemeModel] = relationship(
        back_populates="questions",
    )


class QuestionToThemeModel(BaseModel):
    __tablename__ = "question_to_theme"
    __table_args__ = (
        PrimaryKeyConstraint(
            "round_id",
            "theme_id",
            "question_id",
            name="pk_question_to_theme",
        ),
    )

    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"))
    theme_id: Mapped[int] = mapped_column(ForeignKey("theme.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))

    status: Mapped[AnswerStatusEnum] = mapped_column(
        PgEnum(AnswerStatusEnum),
        default=AnswerStatusEnum.NOT_ANSWERED,
    )
    question: Mapped[QuestionModel] = relationship()
    theme: Mapped[ThemeModel] = relationship()


class RoundToGameModel(BaseModel):
    __tablename__ = "round_to_game"

    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"), primary_key=True)


class ThemeToRoundModel(BaseModel):
    __tablename__ = "theme_to_round"

    theme_id: Mapped[int] = mapped_column(ForeignKey("theme.id"), primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), primary_key=True)


class TelegramUserToRoundModel(BaseModel):
    __tablename__ = "telegram_user_to_round"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_user.id"),
        primary_key=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id"),
        primary_key=True,
    )
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), primary_key=True)
    state: Mapped[AnswerStatusEnum] = mapped_column(
        PgEnum(AnswerStatusEnum),
        default=AnswerStatusEnum.NOT_ANSWERED,
    )

    question: Mapped[QuestionModel] = relationship()


class TimersModel(BaseModel):
    __tablename__ = "timers"

    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), primary_key=True)
    create_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))
    duration: Mapped[timedelta] = mapped_column(Interval)
