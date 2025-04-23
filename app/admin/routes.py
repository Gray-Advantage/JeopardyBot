import typing

if typing.TYPE_CHECKING:
    from app.app import Application


def setup_routes(app: "Application"):
    from app.admin.views import (
        AdminCurrentView,
        AdminLoginView,
        QuestionsView,
        ThemesView,
    )

    app.router.add_view("/admin/current", AdminCurrentView)
    app.router.add_view("/admin/login", AdminLoginView)
    app.router.add_view("/admin/questions", QuestionsView)
    app.router.add_view("/admin/themes", ThemesView)
