from aiohttp.web import Application as AiohttpApplication

from app.core.config import Config, setup_config
from app.core.database.database import Database, setup_database
from app.core.store import Store, setup_store


class Application(AiohttpApplication):
    database: Database
    config: Config
    store: Store


app = Application()


def setup_app() -> Application:
    setup_config(app)
    setup_database(app)
    setup_store(app)
    return app
