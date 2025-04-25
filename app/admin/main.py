from aiohttp.web import run_app

from app.app import setup_app

if __name__ == "__main__":
    app = setup_app()

    app.database.connect()
    app.on_startup.append(app.accessors.admin_accessor.connect)

    run_app(app)