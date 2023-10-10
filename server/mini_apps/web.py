import aiohttp.web

from .service import Service, ServiceStatus


class View:
    def __init__(self, url, methods, name, handler):
        self.url = url
        self.handler = handler
        self.name = name
        self.methods = methods

    def bound_handler(self, obj):
        return self.handler.__get__(obj, obj.__class__)


class MetaWebApp(type):
    """
    Metaclass for telegram bot to allow automatic registration of commands from methods
    """
    def __new__(cls, name, bases, attrs):
        views = []
        for base in bases:
            base_views = getattr(base, "views", {})
            views.update(base_views)

        for attr in attrs.values():
            view = getattr(attr, "view", None)
            if view and isinstance(view, View):
                views.append(view)

        attrs["views"] = view

        return super().__new__(cls, name, bases, attrs)


class WebApp(Service, metaclass=MetaWebApp):
    views = []

    def __init__(self, settings, name):
        super().__init__(settings, name)

    def add_routes(self, http):
        app = aiohttp.web.Application()

        self.prepare_app(app)

        for view in self.views:
            for methods in view.methods:
                app.router.add_route(method, view.url, view.bound_handler(self), view.name)

        http.app.add_subapp("/%s" % self.name, app)

    def prepare_app(self, app: aiohttp.web.Application):
        pass

    @staticmethod
    def view(url, methdods=["get"], name=None):
        """
        Decorator to register a method as URL handler
        """
        def deco(func):
            func.view = View(url, methdods, name, func)
            return func
        return deco
