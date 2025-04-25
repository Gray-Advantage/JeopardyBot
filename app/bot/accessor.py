from typing import cast

from sqlalchemy import exists, func, insert, select, update
from sqlalchemy.orm import selectinload

from app.bot.models import (
    AnswerStatusEnum,
    GameModel,
    GameStatusEnum,
    QuestionModel,
    QuestionToThemeModel,
    RoundModel,
    RoundToGameModel,
    RoundTypeEnum,
    TelegramUserModel,
    TelegramUserToGameModel,
    TelegramUserToRoundModel,
    ThemeModel,
    ThemeToRoundModel,
)
from app.bot.schemas import Chat, Message, User
from app.core.accessor_base import BaseAccessor


class UserAccessor(BaseAccessor):
    async def get_or_create(self, tele_user: User) -> TelegramUserModel:
        exp = select(TelegramUserModel).where(TelegramUserModel.id == tele_user.id)
        if (user := await self.scalar(exp)) is not None:
            return cast(TelegramUserModel, user)

        exp1 = (
            insert(TelegramUserModel)
            .values(id=tele_user.id, username=tele_user.username)
            .returning(TelegramUserModel)
        )
        return cast(TelegramUserModel, await self.scalar(exp1))

    async def get_by_id(self, user_id: int) -> TelegramUserModel:
        exp = select(TelegramUserModel).where(TelegramUserModel.id == user_id)
        return await self.scalar(exp)


class GameAccessor(BaseAccessor):  # noqa: PLR0904
    async def complete(self, game: GameModel) -> None:
        exp = (
            update(GameModel)
            .where(GameModel.id == game.id)
            .values(status=GameStatusEnum.COMPLETED)
        )
        await self.execute(exp)

    async def get_active_game(self, chat: Chat) -> GameModel | None:
        exp = (
            select(GameModel)
            .where(GameModel.chat_id == chat.id)
            .where(GameModel.status != GameStatusEnum.COMPLETED)
        )
        return await self.scalar(exp)

    async def get(self, chat_id: int, master_id: int) -> GameModel | None:
        exp = (
            select(GameModel)
            .where(GameModel.chat_id == chat_id)
            .where(GameModel.master_id == master_id)
            .where(GameModel.status != GameStatusEnum.COMPLETED)
        )
        return await self.scalar(exp)

    async def get_by_id(self, game_id: int) -> GameModel | None:
        return await self.scalar(select(GameModel).where(GameModel.id == game_id))

    async def create(self, chat_id: int, master_id: int) -> GameModel:
        if (game := await self.get(chat_id, master_id)) is not None:
            return game

        exp = (
            insert(GameModel)
            .values(chat_id=chat_id, master_id=master_id, status=GameStatusEnum.LOBBY)
            .returning(GameModel)
        )
        return cast(GameModel, await self.scalar(exp))

    async def add_player(self, user: User, game_chat: Chat) -> bool:
        await self.app.accessors.user_accessor.get_or_create(user)
        exp = (
            select(TelegramUserToGameModel)
            .join(GameModel, TelegramUserToGameModel.game_id == GameModel.id)
            .where(TelegramUserToGameModel.user_id == user.id)
            .where(GameModel.chat_id == game_chat.id)
            .where(GameModel.status == GameStatusEnum.LOBBY)
        )
        if await self.scalar(exp) is None:
            game_id_stmt = (
                select(GameModel.id)
                .where(GameModel.chat_id == game_chat.id)
                .where(GameModel.status == GameStatusEnum.LOBBY)
            )
            game_id = await self.scalar(game_id_stmt)
            if game_id is None:
                return False

            insert_stmt = insert(TelegramUserToGameModel).values(
                user_id=user.id,
                game_id=game_id,
            )
            await self.execute(insert_stmt)
            return True
        return False

    async def all_users(self, chat: Chat) -> list[TelegramUserModel]:
        exp = (
            select(TelegramUserModel)
            .join(
                TelegramUserToGameModel,
                TelegramUserToGameModel.user_id == TelegramUserModel.id,
            )
            .join(GameModel, TelegramUserToGameModel.game_id == GameModel.id)
            .where(GameModel.chat_id == chat.id)
            .where(GameModel.status != GameStatusEnum.COMPLETED)
        )
        return list(await self.scalars(exp))

    async def next_round(self, chat: Chat) -> bool:
        game = await self.get_active_game(chat)
        if game is None:
            raise RuntimeError("Game not found")

        if game.status == GameStatusEnum.ROUND_1:
            exp = (
                update(GameModel)
                .where(GameModel.id == game.id)
                .values(status=GameStatusEnum.COMPLETED)
            )
            await self.execute(exp)
            return False  # Next?

        exp = (
            update(GameModel)
            .where(GameModel.id == game.id)
            .values(status=GameStatusEnum.ROUND_1)
        )
        await self.execute(exp)

        exp1 = (
            insert(RoundModel).values(type=RoundTypeEnum.ROUND_1).returning(RoundModel)
        )
        round_ = await self.scalar(exp1)
        if round_ is None:
            raise RuntimeError("Round not found")

        exp2 = (
            insert(RoundToGameModel)
            .values(game_id=game.id, round_id=round_.id)
            .returning(RoundToGameModel)
        )
        await self.execute(exp2)

        exp3 = (
            select(ThemeModel)
            .options(selectinload(ThemeModel.questions))
            .order_by(func.random())
            .limit(3)
        )
        themes = await self.scalars(exp3)

        for theme in themes:
            exp4 = insert(ThemeToRoundModel).values(
                theme_id=theme.id, round_id=round_.id
            )
            await self.execute(exp4)

            for question in theme.questions:
                exp5 = insert(QuestionToThemeModel).values(
                    question_id=question.id,
                    theme_id=theme.id,
                    round_id=round_.id,
                )
                await self.execute(exp5)
        return True  # Next?

    async def get_current_round(self, chat: Chat) -> RoundModel:
        game = await self.get_active_game(chat)
        exp = (
            select(RoundModel)
            .join(RoundToGameModel, RoundModel.id == RoundToGameModel.round_id)
            .where(
                RoundModel.type == game.status,
                RoundToGameModel.game_id == game.id,
            )
        )
        return await self.scalar(exp)

    async def all_questions(self, chat: Chat) -> list[list[QuestionToThemeModel]]:
        round_ = await self.get_current_round(chat)
        if round_ is None:
            return []

        stmt = (
            select(QuestionToThemeModel)
            .where(QuestionToThemeModel.round_id == round_.id)
            .options(
                selectinload(QuestionToThemeModel.question),
                selectinload(QuestionToThemeModel.theme),
            )
            .order_by(QuestionToThemeModel.theme_id)
        )

        records = await self.scalars(stmt)

        grouped: dict[int, list[QuestionToThemeModel]] = {}
        for item in records:
            grouped.setdefault(item.theme_id, []).append(item)

        return list(grouped.values())

    async def set_choice_user(
        self,
        chat: Chat,
        choice: TelegramUserModel,
    ) -> TelegramUserModel:
        game = await self.get_active_game(chat)

        exp = (
            update(GameModel)
            .where(GameModel.id == game.id)
            .values(choice_user_id=choice.id)
        )
        await self.execute(exp)
        return choice

    async def set_active_user_null(self, chat: Chat) -> None:
        game = await self.get_active_game(chat)

        exp = (
            update(GameModel).where(GameModel.id == game.id).values(active_user_id=None)
        )
        await self.execute(exp)

    async def set_active_user(
        self,
        chat: Chat,
        active: User,
        user_id: int,
        question_id: int,
        round_id: int,
    ) -> None:
        game = await self.get_active_game(chat)

        exp = (
            update(GameModel)
            .where(GameModel.id == game.id)
            .values(active_user_id=active.id)
        )
        await self.execute(exp)

        exp1 = (
            update(TelegramUserToRoundModel)
            .where(
                TelegramUserToRoundModel.user_id == user_id,
                TelegramUserToRoundModel.question_id == question_id,
                TelegramUserToRoundModel.round_id == round_id,
            )
            .values(state=AnswerStatusEnum.WAIT_ANSWERED)
        )
        await self.execute(exp1)

    async def get_question_by_message(
        self, msg_or_call: Message
    ) -> QuestionModel:
        round_ = await self.get_current_round(msg_or_call.chat)

        exp1 = (
            select(TelegramUserToRoundModel)
            .where(TelegramUserToRoundModel.user_id == msg_or_call.from_.id)
            .where(TelegramUserToRoundModel.round_id == round_.id)
            .where(TelegramUserToRoundModel.state == AnswerStatusEnum.WAIT_ANSWERED)
        )
        res = await self.scalar(exp1)
        question_id, round_id = res.question_id, res.round_id

        exp2 = select(QuestionModel).where(QuestionModel.id == question_id)
        theme_id = (await self.scalar(exp2)).theme_id

        exp = select(QuestionToThemeModel).where(
            QuestionToThemeModel.round_id == round_id,
            QuestionToThemeModel.theme_id == theme_id,
            QuestionToThemeModel.question_id == question_id,
        )
        question_to_theme = await self.scalar(exp)

        exp1 = (
            select(QuestionModel)
            .options(selectinload(QuestionModel.theme))
            .where(QuestionModel.id == question_to_theme.question_id)
        )

        return await self.scalar(exp1)

    async def get_active_user(self, chat: Chat) -> TelegramUserModel | None:
        game = await self.get_active_game(chat)
        if game is None:
            return None

        exp = select(TelegramUserModel).where(
            TelegramUserModel.id == game.active_user_id
        )
        return await self.scalar(exp)

    async def set_user_answered(
        self,
        user_id: int,
        question_id: int,
        round_id: int,
    ) -> None:
        exp = (
            update(TelegramUserToRoundModel)
            .where(
                TelegramUserToRoundModel.user_id == user_id,
                TelegramUserToRoundModel.question_id == question_id,
                TelegramUserToRoundModel.round_id == round_id,
            )
            .values(state=AnswerStatusEnum.ANSWERED)
        )
        await self.execute(exp)

    async def is_answered(self, user_id: int, question_id: int, round_id: int) -> bool:
        exp = select(TelegramUserToRoundModel).where(
            TelegramUserToRoundModel.user_id == user_id,
            TelegramUserToRoundModel.question_id == question_id,
            TelegramUserToRoundModel.round_id == round_id,
            TelegramUserToRoundModel.state == AnswerStatusEnum.ANSWERED,
        )
        return await self.scalar(exp) is not None

    async def get_question_by_user_round(
        self,
        user_id: int,
        question_id: int,
        round_: RoundModel,
    ) -> QuestionModel:
        exp = (
            select(TelegramUserToRoundModel)
            .options(selectinload(TelegramUserToRoundModel.question))
            .where(
                TelegramUserToRoundModel.user_id == user_id,
                TelegramUserToRoundModel.round_id == round_.id,
                TelegramUserToRoundModel.question_id == question_id,
                TelegramUserToRoundModel.state == AnswerStatusEnum.ANSWERED,
            )
        )
        res = await self.scalar(exp)
        return res.question

    async def add_score(self, user_id: int, game_id: int, score: int) -> None:
        exp = (
            update(TelegramUserToGameModel)
            .where(
                TelegramUserToGameModel.user_id == user_id,
                TelegramUserToGameModel.game_id == game_id,
            )
            .values(
                score=TelegramUserToGameModel.score + score,
            )
        )
        await self.execute(exp)

    async def set_question_answered(
        self, theme_id: int, question_id: int, round_id: int
    ) -> None:
        exp = (
            update(QuestionToThemeModel)
            .where(
                QuestionToThemeModel.theme_id == theme_id,
                QuestionToThemeModel.question_id == question_id,
                QuestionToThemeModel.round_id == round_id,
            )
            .values(status=AnswerStatusEnum.ANSWERED)
        )
        await self.execute(exp)

    async def has_questions(self, round_: RoundModel) -> bool:
        exp = select(
            exists(QuestionToThemeModel).where(
                QuestionToThemeModel.round_id == round_.id,
                QuestionToThemeModel.status == AnswerStatusEnum.NOT_ANSWERED,
            ),
        )
        return await self.scalar(exp)

    async def all_profiles(self, game_id: int) -> list[TelegramUserToGameModel]:
        exp = (
            select(TelegramUserToGameModel)
            .options(selectinload(TelegramUserToGameModel.user))
            .where(TelegramUserToGameModel.game_id == game_id)
        )
        return list(await self.scalars(exp))

    async def summarize(self, profile: TelegramUserToGameModel, is_win: bool) -> None:
        exp = (
            update(TelegramUserModel)
            .where(TelegramUserModel.id == profile.user_id)
            .values(
                score=TelegramUserModel.score + profile.score,
                win_count=(
                    TelegramUserModel.win_count + 1
                    if is_win
                    else TelegramUserModel.win_count
                ),
                loss_count=(
                    TelegramUserModel.loss_count + 1
                    if not is_win
                    else TelegramUserModel.loss_count
                ),
            )
        )
        await self.execute(exp)

    async def generate_users_answer_status(
        self,
        chat: Chat,
        question_id: int,
        round_id: int,
    ) -> None:
        users = await self.all_users(chat)

        for user in users:
            exp = insert(TelegramUserToRoundModel).values(
                user_id=user.id,
                question_id=question_id,
                round_id=round_id,
            )
            await self.execute(exp)

    async def has_user_not_answered(self, round_id: int, question_id: int) -> bool:
        exp = select(
            exists(TelegramUserToRoundModel).where(
                TelegramUserToRoundModel.question_id == question_id,
                TelegramUserToRoundModel.round_id == round_id,
                TelegramUserToRoundModel.state == AnswerStatusEnum.NOT_ANSWERED,
            )
        )
        return await self.scalar(exp)

    async def has_answer(self, user_id: int, round_id: int, question_id: int) -> bool:
        exp = (
            select(TelegramUserToRoundModel)
            .where(
                TelegramUserToRoundModel.user_id == user_id,
                TelegramUserToRoundModel.question_id == question_id,
                TelegramUserToRoundModel.round_id == round_id,
            )
        )
        return (await self.scalar(exp)).state == AnswerStatusEnum.ANSWERED

    async def get_question_by_id(self, question_id: int) -> QuestionModel:
        exp = (
            select(QuestionModel)
            .where(QuestionModel.id == question_id)
        )
        return await self.scalar(exp)
