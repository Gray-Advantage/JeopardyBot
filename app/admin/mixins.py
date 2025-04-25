from aiohttp.web_exceptions import HTTPUnauthorized
from aiohttp_session import get_session
from app.app import app


class AuthRequiredMixin:
    async def _iter(self):
        session = await get_session(request=self.request)
        admin_email = session.get("admin_email", None)

        if admin_email is None:
            raise HTTPUnauthorized()

        admin = await app.accessors.admin_accessor.get_by_email(admin_email)

        if admin is None:
            raise HTTPUnauthorized()

        self.request.admin = admin

        return await super()._iter()
