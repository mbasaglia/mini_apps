import aiohttp

from mini_apps.web import JinjaApp, view


class ControllerApp(WebApp):
    @view("/")
    def index(self, request):
        pass
