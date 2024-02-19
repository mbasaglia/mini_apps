import json
import pprint
import pathlib
import datetime
import functools
import traceback

import aiohttp.web
import aiohttp_jinja2

import jinja2
from markupsafe import Markup

from ..service import Service, ServiceStatus, Client
from ..apps.auth.user import UserFilter
from .utils import ExtendedApplication
from .route_info import RouteInfo


class ViewHandler:
    def __init__(self, instance: "WebApp", handler):
        self.handler = handler.__get__(instance, instance.__class__)
        self.instance = instance

    async def __call__(self, request: aiohttp.web.Request):
        return await self.instance.handler_wrapper(self.handler, request, **request.match_info)


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


def meta_webapp(name, bases, attrs):
    """
    Metaclass for telegram bot to allow automatic registration of commands from methods
    """
    views = []
    for base in bases:
        base_views = getattr(base, "views", [])
        views += base_views

    for attr in attrs.values():
        view = getattr(attr, "view", None)
        if view and isinstance(view, View):
            views.append(view)

    attrs["views"] = views


def view_decorator(func, url=None, methods=["get"], name=None):
    if url is None:
        url = "/%s/" % func.__name__
    func.view = View(url, methods, name, func)
    return func


def view(url=None, methods=["get"], name=None):
    """
    Decorator to register a method as URL handler
    """
    def deco(func):
        return view_decorator(func, url, methods, name)

    if callable(url):
        return view_decorator(url, None, methods, name)

    return deco


def template_view(*args, template, **kwargs):
    """
    View rendered with a Jinja2 template
    """
    def deco(func):
        @functools.wraps(func)
        async def handler(self, request, **func_kwargs):
            context = await func(self, request, **func_kwargs)
            response = aiohttp_jinja2.render_template(template, request, context)
            return response
        return view_decorator(handler, *args, **kwargs)

    return deco


class WebApp(Service):
    """
    Web app
    """
    views = []
    meta_processors = set([meta_webapp])

    def __init__(self, settings):
        super().__init__(settings)
        self.prefix = self.settings.get("prefix", "/" + self.name)

    def consumes(self):
        return super().consumes() + ["http"]

    def on_provider_added(self, provider):
        super().on_provider_added(provider)
        if provider.name == "http":
            http = provider.service
            self.http = http

            self.url = self.settings.get("url")
            if not self.url:
                self.url = http.base_url
                if self.prefix:
                    self.url += self.prefix
                self.url += "/"

            self.add_routes(http)

    def add_routes(self, http):
        """
        Registers routes to the web server
        """
        app = ExtendedApplication()

        self.prepare_app(http, app)

        for view in self.views:
            methods = list(view.methods)
            if "get" in methods:
                methods.append("head")
            for method in methods:
                app.router.add_route(method, view.url, view.bound_handler(self), name=view.name)

        http.app.add_named_subapp(self.prefix, self.name, app)
        self.app = app

    def route_info(self):
        return [RouteInfo(self.prefix, self.name, "app", None)] + RouteInfo.from_app(self.app)

    @property
    def runnable(self):
        return False

    def prepare_app(self, http, app: ExtendedApplication):
        """
        Prepares the http app
        """
        pass

    async def run(self):
        self.status = ServiceStatus.Running

    async def handler_wrapper(self, handler, request, **kwargs):
        """
        Invokes the actual handler and manages exception
        """
        try:
            return await handler(request, **kwargs)
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

    def get_url(self, url_name, **kwargs):
        if url_name in self.app.router.named_resources():
            kwargs["app"] = self.app
        return str(self.http.url(url_name, **kwargs))


def format_minutes(minutes):
    if minutes < 60:
        return "%s'" % minutes

    hours = minutes // 60
    minutes = minutes % 60
    if minutes:
        return "%d:%02dh" % (hours, minutes)

    return "%dh" % hours


def smart_to_json(value):
    if hasattr(value, "__json__"):
        return value.__json__()
    elif isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    else:
        raise ValueError(value)


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
            context_processors=[m.process_context for m in http.middleware] + [self.context_processor],
            autoescape=jinja2.select_autoescape(),
        )

    def get_template(self, name):
        env = aiohttp_jinja2.get_env(self.app)
        return env.get_template(name)

    async def render_template(self, template, context):
        """
        Render a jinja template to string
        """
        if isinstance(template, str):
            template = self.get_template(template)
        ctx = await self.context_processor(None)
        ctx.update(context)
        return template.render(ctx)

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
            self.get_server_path() / "templates",
            self.get_server_path(),
        ]

        path_set = set(template_paths)
        for path in self.http.common_template_paths:
            if path not in path_set:
                template_paths.append(path)

        return template_paths

    async def context_processor(self, request: aiohttp.web.Request):
        """
        Jinja context processor
        """
        return {
            "app": self,
            "settings": self.settings,
            "request": request,
            "url": self.get_url,
            "minutes": format_minutes,
            "json_dump": lambda v: Markup(json.dumps(v, default=smart_to_json)),
            "hasattr": hasattr,
        }

    async def exception_debug_response(self, request):
        """
        Should render a repsonse detailing the current exception
        """
        body = "Exception:\n\n"
        body += traceback.format_exc()
        body += "\nContext:\n\n"
        body += pprint.pformat(request.get(aiohttp_jinja2.REQUEST_CONTEXT_KEY))
        env = aiohttp_jinja2.get_env(self.app)
        if isinstance(env.loader, jinja2.loaders.FileSystemLoader):
            body += "\n\nTemplate Paths:\n\n"
            body += pprint.pformat(env.loader.searchpath)
        return aiohttp.web.Response(body=body, status=500)


class ServiceWithUserFilter(Service):
    """
    Service with the ability to filter users
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.filter = UserFilter.from_settings(settings)


class SocketService(ServiceWithUserFilter):
    """
    Service that can handle socket connections
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.clients = {}

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        pass

    async def login(self, client: Client, message: dict):
        """Login logic

        :param client: Client requesting to log in
        :param message: Data as sent from the client
        """
        client.user = self.filter.filter_user(self.get_user(message))
        if client.user:
            self.clients[client.id] = client

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the mini app initData
        Return None if authentication fails, otherwise return a user object
        """
        return None

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Override to handle socket messages
        """
        pass

    async def disconnect(self, client: Client):
        """
        Disconnects the given client
        """
        self.clients.pop(client.id)
        self.log.debug("#%s Disconnected", client.id)
        await self.on_client_disconnected(client)

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        pass

    def consumes(self):
        return super().consumes() + ["websocket"]
