import aiohttp

from mini_apps.web import template_view, JinjaApp
from mini_apps.apps.auth.auth import require_admin
from mini_apps.telegram import TelegramBot


def admin_view(*args, **kwargs):
    def deco(func):
        return require_admin(template_view(*args, **kwargs)(func))
    return deco


class AdminApp(JinjaApp):
    def context(self, title, dict):
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

        return self.context("Services", {
            "services": services,
            "bots": bots,
        })
