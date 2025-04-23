from typing import TYPE_CHECKING

from aiohttp_session import setup as aiohttp_setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

if TYPE_CHECKING:
    from app.app import Application


def setup_session(app: 'Application', key: str) -> None:
    f_key = fernet.Fernet(key)
    aiohttp_setup_session(app, EncryptedCookieStorage(f_key))
