import aiohttp

from mini_apps.web import JinjaApp, view, template_view


class AuthApp(JinjaApp):
    @template_view(template="login.jinja2", name="login")
    def login(self, request):
        return {}
