import typing
from functools import cached_property

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL

if typing.TYPE_CHECKING:
    from app.app.app import Application


class BotConfig(BaseModel):
    token: str = "..."


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "project"

    @cached_property
    def url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )


class Config(BaseSettings):
    bot: BotConfig | None = None
    database: DatabaseConfig | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../../../../.env"),  # Если main / если миграции
        env_nested_delimiter="__",
    )


def setup_config(app: "Application") -> None:
    app.config = Config()
