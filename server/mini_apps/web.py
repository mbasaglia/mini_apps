import pprint
import pathlib
import functools
import traceback

import aiohttp.web
import aiohttp.web_urldispatcher
import aiohttp_jinja2

import jinja2

from .service import Service, ServiceStatus


class FileResource(aiohttp.web_urldispatcher.PlainResource):
    def __init__(self, prefix: str, file, name: str = None):
        super().__init__(prefix, name=name)
        self.file = file
        self.register_route(aiohttp.web_urldispatcher.ResourceRoute("GET", self._handle, self))
        self.register_route(aiohttp.web_urldispatcher.ResourceRoute("HEAD", self._handle, self))

    def get_info(self):
        return {
            "file": self.file,
            "prefix": self._path
        }

    async def _handle(self, request: aiohttp.web.Request):
        return aiohttp.web.FileResponse(self.file)


class ViewHandler:
    def __init__(self, instance: "WebApp", handler):
        self.handler = handler.__get__(instance, instance.__class__)
        self.instance = instance

    async def __call__(self, request):
        return await self.instance.handler_wrapper(self.handler, request)


class View:
    def __init__(self, url, methods, name, handler):
        self.url = url
        self.handler = handler
        self.name = name
        self.methods = methods

    def bound_handler(self, obj):
        return functools.wraps(self.handler)(ViewHandler(obj, self.handler))

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
        async def handler(self, request):
            context = await func(self, request)
            request.jinja_context = context
            response = aiohttp_jinja2.render_template(template, request, context)
            return response
        return view_decorator(handler, *args, **kwargs)

    return deco


class ExtendedApplication(aiohttp.web.Application):
    """
    aiohttp application with extra stuff
    """
    def add_static_path(self, prefix, path: pathlib.Path):
        """
        Registers a static path to the app
        """
        if path.is_file():
            self.router.register_resource(FileResource("/", path))
        else:
            self.router.add_static("/", path)

    def add_named_subapp(self, name, app: aiohttp.web.Application):
        # Work around aiohttp add_aubapp so we can set the subapp name
        resource = aiohttp.web.PrefixedSubAppResource("/%s" % name, app)
        resource._name = self.name
        self.router.register_resource(resource)
        self._reg_subapp_signals(app)
        self._subapps.append(app)
        app.pre_freeze()


class WebApp(Service, metaclass=MetaWebApp):
    """
    Web app
    """
    views = []

    def __init__(self, settings):
        super().__init__(settings)

    @property
    def accepts_http(self):
        return True

    def add_routes(self, http):
        """
        Registers routes to the web server
        """

        app = ExtendedApplication()
        self.http = http

        self.prepare_app(http, app)

        for view in self.views:
            for method in view.methods:
                app.router.add_route(method, view.url, view.bound_handler(self), name=view.name)

        http.app.add_named_subapp(self.name, app)

    def prepare_app(self, http, app: ExtendedApplication):
        """
        Prepares the http app
        """
        pass

    async def run(self):
        self.status = ServiceStatus.Running

    async def handler_wrapper(self, handler, request):
        """
        Invokes the actual handler and manages exception
        """
        try:
            return await handler(request)
        except Exception:
            return await self.on_http_exception(request)

    async def on_http_exception(self, request):
        """
        Invoked on http handler exception
        """
        self.log_exception()
        if self.settings.get("debug"):
            return await self.exception_debug_response(request)
        return aiohttp.web.HTTPInternalServerError()

    async def exception_debug_response(self, request):
        """
        Should render a repsonse detailing the current exception
        """
        return aiohttp.web.Response(body=traceback.format_exc(), status=500)


class JinjaApp(WebApp):
    """
    Web app that uses Jinja2 templates
    """

    def prepare_app(self, http, app: ExtendedApplication):
        paths = self.template_paths()

        extra = self.settings.get("template_paths")
        if extra:
            paths += list(map(pathlib.Path, extra))

        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(paths),
            context_processors=[m.process_context for m in http.middleware] + [self.context_processor]
        )

    def template_paths(self):
        """
        Returns the jinja2 template search paths
        """
        template_paths = []

        paths = self.settings.get("templates")
        if paths:
            template_paths += [self.settings.paths.root / path for path in paths]

        template_paths += [
            self.settings.paths.root / "templates",
            self.get_server_path() / "templates"
        ]

        template_paths += self.http.common_template_paths

        return template_paths

    async def context_processor(self, request: aiohttp.web.Request):
        """
        Jinja context processor
        """
        return {
            "app": self,
            "settings": self.settings,
            "request": request,
            "url": self.url
        }

    def url(self, name, **kwargs):
        if name in self.app.router.named_resources():
            kwargs["app"] = self.app
        return self.http.url(name, **kwargs)

    async def exception_debug_response(self, request):
        """
        Should render a repsonse detailing the current exception
        """
        body = traceback.format_exc()
        body += "\nContext:\n"
        body += pprint.pformat(getattr(request, "jinja_context", None))
        env = aiohttp_jinja2.get_env(self.app)
        if isinstance(env.loader, jinja2.loaders.FileSystemLoader):
            body += "\nTemplate Paths:\n"
            body += pprint.pformat(env.loader.searchpath)
        return aiohttp.web.Response(body=body, status=500)
