import typing
from functools import cached_property

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL

if typing.TYPE_CHECKING:
    from app.app import Application


class SessionConfig(BaseModel):
    key: str


class BotConfig(BaseModel):
    token: str = "..."


class AdminConfig(BaseSettings):
    login: str = "admin"
    password: str = "admin"


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


class RabbitmqConfig(BaseModel):
    host: str = "localhost"
    port: int = 5672
    user: str = "guest"
    password: str = "guest"
    input_queue: str = "input_queue"
    output_queue: str = "output_queue"

    @cached_property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}"


class Config(BaseSettings):
    session: SessionConfig
    admin: AdminConfig
    bot: BotConfig
    database: DatabaseConfig
    rabbitmq: RabbitmqConfig

    model_config = SettingsConfigDict(
        # Если main / если poller / если миграции
        env_file=(".env", "../../.env", "../../../../.env"),
        env_nested_delimiter="__",
    )


def setup_config(app: "Application") -> None:
    app.config = Config()
