from typing import TYPE_CHECKING, Any

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.database.sqlalchemy_base import BaseModel

if TYPE_CHECKING:
    from app.app.app import Application


class Database:
    def __init__(self, app: "Application") -> None:
        self.app = app

        self.engine: AsyncEngine | None = None
        self._db: type[DeclarativeBase] = BaseModel
        self.session: async_sessionmaker[AsyncSession] | None = None

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        if self.app.config is None or self.app.config.database is None:
            raise ValueError("Configuration or Database is not properly initialized.")

        self.engine = create_async_engine(
            URL.create(
                drivername="postgresql+asyncpg",
                username=self.app.config.database.user,
                password=self.app.config.database.password,
                host=self.app.config.database.host,
                port=self.app.config.database.port,
                database=self.app.config.database.database,
            ),
            echo=True,
            future=True,
        )
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def disconnect(self, *args: Any, **kwargs: Any) -> None:
        if self.engine is None:
            raise ValueError("Engine is not properly initialized.")

        await self.engine.dispose()


def setup_database(app: "Application") -> None:
    app.database = Database(app)