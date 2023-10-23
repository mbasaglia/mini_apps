import io
import aiohttp

from mini_apps.web import template_view, JinjaApp, view
from mini_apps.apps.auth.auth import require_admin
from mini_apps.telegram import TelegramBot
# from . import messages


def admin_view(*args, **kwargs):
    def deco(func):
        kwargs.setdefault("name", func.__name__)
        return require_admin(template_view(*args, **kwargs)(func))
    return deco


class AdminApp(JinjaApp):
    def __init__(self, settings):
        super().__init__(settings)
        self.bot_pics = {}

    def context(self, title, **dict):
        dict.update(
            static=self.url + "static/",
            title=title,
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
        )

    def get_bot(self, request: aiohttp.web.Request) -> TelegramBot:
        name = request.match_info["name"]
        bot = self.settings.apps.get(name)
        if not isinstance(bot, TelegramBot):
            raise aiohttp.web.HTTPNotFound()
        return bot

    @view("/bot/{name}/picture.jpg", name="bot_picture")
    async def bot_picture(self, request: aiohttp.web.Request):
        bot = self.get_bot(request)
        if bot.name not in self.bot_pics:
            file = io.BytesIO()
            await bot.telegram.download_profile_photo(bot.telegram_me, file, download_big=False)
            self.bot_pics[bot.name] = file.getvalue()

        return aiohttp.web.Response(body=self.bot_pics[bot.name], content_type="image/jpeg")

    @admin_view("/bot/{name}/", template="details.html")
    async def bot_details(self, request):
        bot = self.get_bot(request)
        commands = await bot.get_commands()
        return self.context(
            bot.telegram_me.username,
            bot=bot,
            commands=commands
        )
