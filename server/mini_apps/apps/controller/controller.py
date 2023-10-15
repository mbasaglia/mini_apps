import aiohttp

from mini_apps.web import JinjaApp, view


class ControllerApp(JinjaApp):
    @view("/")
    def index(self, request: aiohttp.web.Request):
        pass
