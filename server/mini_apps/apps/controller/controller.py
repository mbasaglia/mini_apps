import jinja2
import aiohttp
import aiohttp_jinja2

from mini_apps.web import WebApp


class ControllerApp(WebApp):
    def prepare_app(self, app: aiohttp.web.Application):
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(self.get_server_path() / "template")
        )

    @App.view("/")
    def index(self, request):
        pass
