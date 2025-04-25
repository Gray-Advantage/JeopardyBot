from aiohttp.web import (
    Application as AiohttpApplication,
    Request as AiohttpRequest,
    View as AiohttpView,
)

from app.admin.models import AdminModel
from app.admin.routes import setup_routes
from app.bot.manager import TelegramBotManager, setup_bot_api
from app.core.accessor import Accessors, setup_accessors
from app.core.config import Config, setup_config
from app.core.database.database import Database, setup_database
from app.core.session import setup_session


class Application(AiohttpApplication):
    bot_api: TelegramBotManager
    database: Database
    config: Config
    accessors: Accessors


class Request(AiohttpRequest):
    admin: AdminModel | None = None

    @property
    def app(self) -> Application:
        return super().app()


class View(AiohttpView):
    @property
    def request(self) -> Request:
        return super().request

    @property
    def data(self) -> dict:
        return self.request.get("data", {})


app = Application()


def setup_app() -> Application:
    setup_config(app)
    setup_database(app)
    setup_bot_api(app)
    setup_accessors(app)
    setup_session(app, key=app.config.session.key)
    setup_routes(app)
    return app
