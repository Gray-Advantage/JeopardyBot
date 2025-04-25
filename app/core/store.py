import typing

if typing.TYPE_CHECKING:
    from app.app import Application


class Store:  # noqa: B903
    def __init__(self, app: "Application"):
        self.app = app


def setup_store(app: "Application") -> None:
    app.store = Store(app)
