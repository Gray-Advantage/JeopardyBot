from pathlib import Path

from aiohttp.web import run_app

from app.app.app import setup_app

if __name__ == "__main__":
    run_app(setup_app(Path(__file__).resolve().parent / ".env"))
