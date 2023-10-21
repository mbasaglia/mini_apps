import aiohttp

from mini_apps.web import template_view, JinjaApp
from mini_apps.apps.auth.auth import require_admin
from mini_apps.bot import Bot


class ControllerApp(JinjaApp):
    @require_admin
    @template_view("/", template="bot-list.html")
    async def index(self, request: aiohttp.web.Request):
        bots = []
        services = []

        for service in self.server.services.values():
            if isinstance(service.service, Bot):
                bots.append(service.service)
            else:
                services.append(service.service)

        return {
            "services": services,
            "bots": bots,
        }
