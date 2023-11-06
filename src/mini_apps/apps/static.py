from mini_apps.http.web_app import WebApp


class StaticFiles(WebApp):
    def __init__(self, settings):
        super().__init__(settings)
        self.path = settings.paths.root / settings["path"]

    def prepare_app(self, http, app):
        app.router.add_static("/", self.path)
