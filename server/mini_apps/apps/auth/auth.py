import aiohttp
import aiohttp_session

from mini_apps.web import JinjaApp, view, template_view

from mini_apps.middleware.base import Middleware


class AuthMiddleware(Middleware):
    def __init__(self, http):
        app = http.settings.ensure_app(AuthApp, "auth")
        app.middleware = self

    async def needs_login(self, request, handler):
        if not getattr(handler, "requires_auth"):
            request.user = None
            return False

        session = await aiohttp_session.get_session(request)
        request.user = session.get("user")
        if not request.user:
            return True

        if handler.requires_auth_admin and not request.user["is_admin"]:
            return True

        return False

    async def on_process_request(self, request, handler):
        if self.needs_login(request, handler):
            return self.redirect()

        await handler(request)

    def redirect(self, redirect):
        raise aiohttp.web.HTTPSeeOther(self.http.url("login").with_query("redirect", redirect))


class AuthApp(JinjaApp):
    @template_view(template="login.html", name="login")
    async def login(self, request: aiohttp.web.Request):
        return {}

    @view(name="login_auth")
    async def login_auth(self, request: aiohttp.web.Request):
        self.log.info(request.url.query)
        self.middleware.redirect(request.url.query.get("redirect"))


def require_user(func=None, *, is_admin=False):
    def deco(func):
        func.requires_auth = True
        func.requires_auth_admin = is_admin

    if func is not None:
        deco(func)
        return func

    return deco
