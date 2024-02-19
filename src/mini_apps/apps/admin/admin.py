import io
import traceback

import aiohttp

from mini_apps.http.middleware import messages
from mini_apps.http.web_app import template_view, JinjaApp, view
from mini_apps.http.route_info import RouteInfo
from mini_apps.telegram.bot import TelegramBot
from mini_apps.apps.auth.auth import require_admin


def admin_view(*args, **kwargs):
    def deco(func):
        kwargs.setdefault("name", func.__name__)
        if "template" in kwargs:
            inner_deco = template_view(*args, **kwargs)
        else:
            inner_deco = view(*args, **kwargs)
        return require_admin(inner_deco(func))
    return deco


class AdminApp(JinjaApp):
    def __init__(self, settings):
        super().__init__(settings)
        self.bot_pics = {}
        self.show_token = self.settings.get("show-token", True)

    def context(self, title, **dict):
        dict.update(
            static=self.url + "static/",
            title=title,
            show_token=self.show_token
        )
        return dict

    def prepare_app(self, http, app):
        """
        Registers routes to the web server
        """
        super().prepare_app(http, app)
        app.add_static_path("/static", self.get_server_path() / "static")

    @admin_view("/", template="manage.html")
    async def manage(self, request: aiohttp.web.Request):
        bots = []
        services = []

        for service in self.server.services.values():
            if isinstance(service.service, TelegramBot):
                bots.append(service.service)
            else:
                services.append(service.service)

        return self.context(
            "Services",
            services=services,
            bots=bots,
            routes=RouteInfo.from_app(self.http.app),
            http=self.http
        )

    def get_bot(self, name: str) -> TelegramBot:
        bot = self.settings.apps.get(name)
        if not isinstance(bot, TelegramBot):
            raise aiohttp.web.HTTPNotFound()
        return bot

    @admin_view("/bot/{name}/picture.jpg")
    async def bot_picture(self, request: aiohttp.web.Request, name):
        bot = self.get_bot(name)
        if not bot.telegram_me:
            return aiohttp.web.HTTPNotFound()
        if bot.name not in self.bot_pics:
            file = io.BytesIO()
            await bot.telegram.download_profile_photo(bot.telegram_me, file, download_big=False)
            self.bot_pics[bot.name] = file.getvalue()

        return aiohttp.web.Response(body=self.bot_pics[bot.name], content_type="image/jpeg")

    @admin_view("/bot/{name}/", template="details.html")
    async def bot_details(self, request, name):
        bot = self.get_bot(name)
        commands = await bot.get_commands()
        return self.context(
            bot.telegram_me.username if bot.telegram_me else bot.name,
            bot=bot,
            commands=commands,
            info=await bot.info(),
        )

    @admin_view("/bot/{name}/stop/")
    async def bot_stop(self, request, name):
        try:
            await self.server.stop_service(name)
            messages.add_message(request, messages.INFO, "%s stopped" % name)
        except Exception:
            self.log_exception()
            messages.add_message(request, messages.ERROR, "Could not stop %s:\n%s" % (name, traceback.format_exc()))
        return aiohttp.web.HTTPSeeOther(self.get_url("manage"))

    @admin_view("/bot/{name}/start/")
    async def bot_start(self, request, name):
        try:
            self.server.start_service(name)
            messages.add_message(request, messages.INFO, "%s started" % name)
        except Exception:
            self.log_exception()
            messages.add_message(request, messages.ERROR, "Could not start %s:\n%s" % (name, traceback.format_exc()))
        return aiohttp.web.HTTPSeeOther(self.get_url("manage"))

    @admin_view("/bot/{name}/reload/")
    async def bot_restart(self, request, name):
        try:
            await self.server.stop_service(name)
            self.server.start_service(name)
            self.bot_pics.pop(name, None)
            messages.add_message(request, messages.INFO, "%s restarted" % name)
        except Exception:
            self.log_exception()
            messages.add_message(request, messages.ERROR, "Could not restart %s:\n%s" % (name, traceback.format_exc()))
        return aiohttp.web.HTTPSeeOther(self.get_url("manage"))

    @admin_view("/bot/{name}/clear-exceptions/")
    async def bot_clear_exceptions(self, request, name):
        self.get_bot(name).exception_log = ""
        messages.add_message(request, messages.INFO, "Exceptions cleared")
        return aiohttp.web.HTTPSeeOther(self.get_url("bot_details", name=name))
