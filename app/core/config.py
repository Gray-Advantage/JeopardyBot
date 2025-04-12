import typing
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if typing.TYPE_CHECKING:
    from app.app.app import Application


class BotConfig(BaseModel):
    token: str = Field("...", validation_alias="BOT__TOKEN")


class DatabaseConfig(BaseModel):
    host: str = Field("localhost", validation_alias="DATABASE__HOST")
    port: int = Field(5432, validation_alias="DATABASE__PORT")
    user: str = Field("postgres", validation_alias="DATABASE__USER")
    password: str = Field("postgres", validation_alias="DATABASE__PASSWORD")
    database: str = Field("project", validation_alias="DATABASE__DATABASE")


class Config(BaseSettings):
    bot: BotConfig | None = None
    database: DatabaseConfig | None = None
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter='__')


def setup_config(app: "Application", config_path: Path) -> None:
    app.config = Config(_env_file=config_path)
