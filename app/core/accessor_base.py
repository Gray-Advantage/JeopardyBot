from asyncio import current_task
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from sqlalchemy import Row
from sqlalchemy.engine import CursorResult, Result, ScalarResult
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
)
from sqlalchemy.sql.base import Executable

if TYPE_CHECKING:
    from app.app import Application


class BaseAccessor:
    def __init__(self, app: "Application"):
        self.app = app

        self._current_session: ContextVar[AsyncSession | None] = ContextVar(
            "current_session",
            default=None,
        )

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        if self.app.database.session is None:
            raise RuntimeError("DatabaseAccessor is not connected")
        return self.app.database.session

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        scoped_session = async_scoped_session(
            session_factory=self.session_maker,
            scopefunc=current_task,
        )

        async with scoped_session() as session:
            token = self._current_session.set(session)

            yield session
            await session.commit()

            self._current_session.reset(token)
            await scoped_session.remove()

    def get_current_session(self) -> AsyncSession | None:
        return self._current_session.get()

    async def execute(
        self,
        statement: Executable,
    ) -> CursorResult[Any] | Result[Any]:
        session = self.get_current_session()

        if session:
            return await session.execute(statement)

        async with self.session() as session:
            return await session.execute(statement)

    async def scalar(self, statement: Executable) -> Any | None:
        return (await self.execute(statement)).scalar()

    async def scalars(self, statement: Executable) -> ScalarResult[Any]:
        return (await self.execute(statement)).scalars()

    async def one(self, statement: Executable) -> Any:
        return (await self.execute(statement)).one()

    async def one_or_none(self, statement: Executable) -> Any | None:
        return (await self.execute(statement)).one_or_none()

    async def first(self, statement: Executable) -> Any | None:
        return (await self.execute(statement)).first()

    async def all(self, statement: Executable) -> Sequence[Row[Any]]:
        return (await self.execute(statement)).all()
