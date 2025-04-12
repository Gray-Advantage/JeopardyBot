from pathlib import Path

from aiohttp.web import Application as AiohttpApplication

from app.core.config import Config, setup_config
from app.core.database.database import Database, setup_database
from app.core.store import Store, setup_store

__all__ = ("Application", "setup_app")


class Application(AiohttpApplication):
    database: Database | None = None
    config: Config | None = None
    store: Store | None = None


app = Application()


def setup_app(config_path: Path) -> Application:
    setup_config(app, config_path)
    setup_database(app)
    setup_store(app)
    return app
