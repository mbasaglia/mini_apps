import pathlib
import functools

import aiohttp.web
import aiohttp_jinja2

import jinja2

from .service import Service, ServiceStatus


class View:
    def __init__(self, url, methods, name, handler):
        self.url = url
        self.handler = handler
        self.name = name
        self.methods = methods

    def bound_handler(self, obj):
        return self.handler.__get__(obj, obj.__class__)

    def __repr__(self):
        return "View(%s)" % ", ".join(
            "%s=%r" % item for item in vars(self).items()
        )


class MetaWebApp(type):
    """
    Metaclass for telegram bot to allow automatic registration of commands from methods
    """
    def __new__(cls, name, bases, attrs):
        views = []
        for base in bases:
            base_views = getattr(base, "views", [])
            views += base_views

        for attr in attrs.values():
            view = getattr(attr, "view", None)
            if view and isinstance(view, View):
                views.append(view)

        attrs["views"] = views

        return super().__new__(cls, name, bases, attrs)


def view_decorator(func, url=None, methods=["get"], name=None):
    if url is None:
        url = "/%s/" % func.__name__
    func.view = View(url, methods, name, func)
    return func


def view(url=None, methdods=["get"], name=None):
    """
    Decorator to register a method as URL handler
    """
    def deco(func):
        return view_decorator(func, url, methdods, name)

    if callable(url):
        return view_decorator(url, None, methdods, name)

    return deco


def template_view(*args, template, **kwargs):
    """
    View rendered with a Jinja2 template
    """
    def deco(func):
        @functools.wraps(func)
        def handler(self, request):
            context = func(self, request)
            response = aiohttp_jinja2.render_template(template, request, context)
            return response
        return view_decorator(handler, *args, **kwargs)

    return deco


class WebApp(Service, metaclass=MetaWebApp):
    """
    Web app
    """
    views = []

    def __init__(self, settings, name):
        super().__init__(settings, name)

    def add_routes(self, http):
        app = aiohttp.web.Application()
        self.http = http

        self.prepare_app(http, app)

        for view in self.views:
            for method in view.methods:
                app.router.add_route(method, view.url, view.bound_handler(self), name=view.name)

        http.app.add_subapp("/%s" % self.name, app)

    def prepare_app(self, http, app: aiohttp.web.Application):
        """
        Prepares the http app
        """
        pass

    async def run(self):
        self.status = ServiceStatus.Running


class JinjaApp(WebApp):
    """
    Web app that uses Jinja2 templates
    """

    def prepare_app(self, http, app: aiohttp.web.Application):
        paths = self.settings.get("templates")
        if paths:
            paths = [self.settings.paths.root / path for path in paths]
        else:
            paths = [self.get_server_path() / "templates"]

        extra = self.settings.get("template_paths")
        if extra:
            paths += list(map(pathlib.Path, extra))

        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(paths),
            context_processors=[m.process_context for m in http.middleware] + [self.context_processor]
        )

    async def context_processor(self, request: aiohttp.web.Request):
        """
        Jinja context processor
        """
        return {
            "app": self,
            "settings": self.settings,
            "request": request,
            "url": self.http.url
        }
