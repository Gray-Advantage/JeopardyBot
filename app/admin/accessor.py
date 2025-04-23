from typing import cast

from sqlalchemy import insert, select
from sqlalchemy.orm import selectinload

from app.admin.models import AdminModel
from app.bot.models import QuestionModel, ThemeModel
from app.core.accessor_base import BaseAccessor


class AdminAccessor(BaseAccessor):
    async def connect(self, *args, **kwargs) -> None:
        await self.create_admin(
            email=self.app.config.admin.login,
            password=self.app.config.admin.password,
        )

    async def get_by_email(self, email: str) -> AdminModel | None:
        query = select(AdminModel).filter(AdminModel.email == email)
        return await self.scalar(query)

    async def get_by_id(self, admin_id: int) -> AdminModel | None:
        query = select(AdminModel).filter(AdminModel.id == admin_id)
        return (await self.execute(query)).scalar_one_or_none()

    async def create_admin(self, email: str, password: str) -> AdminModel:
        async with self.app.database.session() as session:
            query = select(AdminModel).where(AdminModel.email == email)
            existing = (await session.execute(query)).scalar_one_or_none()

            if existing:
                return existing

            admin = AdminModel(email=email)
            admin.set_password(password)
            session.add(admin)
            await session.commit()
            return admin


class ThemeAccessor(BaseAccessor):
    async def get_theme_by_id(self, theme_id: int) -> ThemeModel | None:
        exp = (
            select(ThemeModel)
            .where(ThemeModel.id == theme_id)
            .options(selectinload(ThemeModel.questions))
        )
        return await self.scalar(exp)

    async def get_all_themes(self) -> list[ThemeModel]:
        exp = select(ThemeModel).options(selectinload(ThemeModel.questions))
        return list(await self.scalars(exp))

    async def get_all_questions(self) -> list[QuestionModel]:
        exp = select(QuestionModel)
        return list(await self.scalars(exp))

    async def create_theme(self, title: str) -> ThemeModel:
        exp = insert(ThemeModel).values(title=title).returning(ThemeModel)
        return cast(ThemeModel, await self.scalar(exp))

    async def get_question_by_id(self, question_id: int) -> QuestionModel | None:
        exp = (
            select(QuestionModel)
            .where(QuestionModel.id == question_id)
            .options(selectinload(QuestionModel.theme))
        )
        return await self.scalar(exp)

    async def get_questions_by_theme(self, theme_id: int) -> list[QuestionModel]:
        exp = (
            select(QuestionModel)
            .where(QuestionModel.theme_id == theme_id)
            .options(selectinload(QuestionModel.theme))
        )
        return list(await self.scalars(exp))

    async def create_question(
        self, text: str, answer: str, hard_level: int, theme_id: int
    ) -> QuestionModel:
        exp = (
            insert(QuestionModel)
            .values(text=text, answer=answer, hard_level=hard_level, theme_id=theme_id)
            .returning(QuestionModel)
        )
        return cast(QuestionModel, await self.scalar(exp))
