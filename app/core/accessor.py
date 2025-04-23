from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.admin.accessor import AdminAccessor, ThemeAccessor
from app.bot.accessor import GameAccessor, UserAccessor
from app.core.accessor_base import BaseAccessor

if TYPE_CHECKING:
    from app.app import Application


@asynccontextmanager
async def transaction(db: BaseAccessor) -> AsyncGenerator[AsyncSession, None]:
    session = db.get_current_session()

    if session:
        async with session.begin_nested():
            yield session
    else:
        async with db.session() as session, session.begin():
            yield session


class Accessors:
    base_accessor: BaseAccessor
    user_accessor: UserAccessor
    game_accessor: GameAccessor
    admin_accessor: AdminAccessor
    theme_accessor: ThemeAccessor

    def __init__(self, app: "Application"):
        self.base_accessor = BaseAccessor(app)
        self.user_accessor = UserAccessor(app)
        self.game_accessor = GameAccessor(app)
        self.admin_accessor = AdminAccessor(app)
        self.theme_accessor = ThemeAccessor(app)


def setup_accessors(app: "Application") -> None:
    app.accessors = Accessors(app)
