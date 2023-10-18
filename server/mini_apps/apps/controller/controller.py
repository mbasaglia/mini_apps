import aiohttp

from mini_apps.web import JinjaApp, template_view
from mini_apps.apps.auth.auth import require_admin


class ControllerApp(JinjaApp):
    @require_admin
    @template_view("/", template="bot-list.html")
    def index(self, request: aiohttp.web.Request):
        return {
            "bots": []
        }
