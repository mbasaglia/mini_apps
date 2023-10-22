from mini_apps.web import WebApp


class MiniAppsCommon(WebApp):
    @classmethod
    def default_name(cls):
        return "mini_apps"

    def prepare_app(self, http, app):
        app.router.add_static("/", self.get_server_path() / "public")
