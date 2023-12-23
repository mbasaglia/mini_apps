import json
import datetime


import aiohttp
import aiohttp_session
from yarl import URL

from mini_apps.http.web_app import JinjaApp, view, template_view
from mini_apps.http.middleware.base import Middleware
from .user import User, UserFilter, clean_telegram_auth


class Auth(JinjaApp, Middleware):
    """
    Middleware thhat handles logins and adds request.user
    """
    auth_key = "__auth"

    def __init__(self, settings):
        super().__init__(settings)
        self.settings = settings
        self.filter = UserFilter.from_settings(self.settings)
        self.cookie_max_age = datetime.timedelta(seconds=self.settings.get("max_age", 24*60*60))
        self.cookie_refresh = self.settings.get("refresh", True)
        self.bot_token = self.settings.get("bot-token")
        self.bot_username = self.settings.get("bot-username")

    async def get_user(self, request):
        session = await aiohttp_session.get_session(request)
        session_user = session.get(self.auth_key)
        if session_user:
            user = User.from_json(session_user)
        else:
            fake_user = self.settings.get("fake-user")
            if not fake_user:
                request.user = None
                return None

            user = User.from_telegram_dict(fake_user)

        request.user = self.filter.filter_user(user)
        return request.user

    async def needs_login(self, request, handler):
        await self.get_user(request)

        if not getattr(handler, "requires_auth", False):
            return False

        if not request.user:
            return True

        if handler.requires_auth_admin and not request.user.is_admin:
            return True

        return False

    async def on_process_request(self, request: aiohttp.web.Request, handler):
        if await self.needs_login(request, handler):
            return self.redirect(request.url)

        response: aiohttp.web.Response = await handler(request)

        if getattr(request, "auth_change", False) or (request.user and self.cookie_refresh):
            response.set_cookie(
                self.auth_key,
                json.dumps(request.user.to_json()) if request.user else "",
                max_age=self.cookie_max_age.total_seconds(),
                httponly=True,
                domain=request.url.raw_authority,
                secure=request.url.scheme == "https",
                samesite="Strict",
            )

        return response

    def redirect(self, redirect):
        if isinstance(redirect, URL):
            redirect = redirect.path
        return aiohttp.web.HTTPSeeOther(self.http.url("%s:login" % self.name).with_query(redirect=redirect))

    async def log_in(self, request, user):
        session = await aiohttp_session.get_session(request)
        user = self.filter.filter_user(user)
        request.user = user
        request.auth_change = True

        if user:
            session[self.auth_key] = user.to_json()
            self.log.info("login from %s", user.to_json())
        else:
            session.pop(self.auth_key, None)

        return user

    async def log_out(self, request):
        await self.log_in(request, None)

    async def on_process_context(self, request):
        return {
            "user": request.user
        }

    def add_routes(self, http):
        http.common_template_paths += self.template_paths()
        return super().add_routes(http)

    @template_view(url="/login", template="login.html", name="login")
    async def login_view(self, request: aiohttp.web.Request):
        return {
            "bot_username": self.bot_username
        }

    @view(name="login_auth")
    async def login_auth(self, request: aiohttp.web.Request):
        data = dict(request.url.query)
        redirect = data.pop("redirect", "")
        self.log.debug(data)
        data = clean_telegram_auth(data, self.bot_token)
        if data:
            user = User.from_telegram_dict(data)
            user.telegram_id = int(user.telegram_id)
            await self.log_in(request, user)
            redirect_path = URL(redirect).path
            return aiohttp.web.HTTPSeeOther(URL(self.http.base_url).with_path(redirect_path))
        else:
            return self.redirect(redirect)

    @view(url="/logout", name="logout")
    async def loggout_view(self, request: aiohttp.web.Request):
        await self.log_out(request)
        return self.redirect(URL(request.headers.get("referer", "")).path)

    def register_consumer(self, what, service):
        pass

    def provides(self):
        return ["auth"]


def require_user(func=None, *, is_admin=False):
    def deco(func):
        func.requires_auth = True
        func.requires_auth_admin = is_admin

    if func is not None:
        deco(func)
        return func

    return deco


def require_admin(func):
    func.requires_auth = True
    func.requires_auth_admin = True
    return func
