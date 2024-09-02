import pathlib

import aiohttp.web
import aiohttp.web_urldispatcher


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

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, " ".join(
            "%s=%r" % i for i in self.get_info()
        ))


class ExtendedApplication(aiohttp.web.Application):
    """
    aiohttp application with extra stuff
    """
    def add_static_path(self, prefix, path: pathlib.Path, *args, **kwargs):
        """
        Registers a static path to the app
        """
        if path.is_file():
            self.router.register_resource(FileResource(prefix, path, *args, **kwargs))
        else:
            self.router.add_static(prefix, path, *args, **kwargs)

    def add_named_subapp(self, prefix, name, app: aiohttp.web.Application):
        # Work around aiohttp add_aubapp so we can set the subapp name
        if prefix:
            resource = aiohttp.web.PrefixedSubAppResource(prefix, app)
            resource._name = name
        else:
            resource = NakedSubAppResource(name, app)

        self.router.register_resource(resource)
        self._reg_subapp_signals(app)
        self._subapps.append(app)
        app.pre_freeze()


class NakedSubAppResource(aiohttp.web_urldispatcher.AbstractResource):
    def __init__(self, name: str, app: aiohttp.web.Application) -> None:
        super().__init__(name=name)
        self.app = app

    @property
    def canonical(self) -> str:
        return "/"

    def add_prefix(self, prefix: str) -> None:
        for resource in self.app.router.resources():
            resource.add_prefix(prefix)

    def url_for(self, *args: str, **kwargs: str):
        raise RuntimeError(".url_for() is not supported " "by sub-application root")

    def get_info(self):
        return {"app": self.app}

    async def resolve(self, request: aiohttp.web.Request):
        match_info = await self.app.router.resolve(request)
        match_info.add_app(self.app)
        if isinstance(match_info.http_exception, aiohttp.web.HTTPMethodNotAllowed):
            methods = match_info.http_exception.allowed_methods
        else:
            methods = set()
        return match_info, methods

    def __len__(self) -> int:
        return len(self.app.router.routes())

    def __iter__(self):
        return iter(self.app.router.routes())

    def __repr__(self) -> str:
        return "<NakedSubAppResource {app!r}>".format(app=self.app)

    def raw_match(self, prefix: str) -> bool:
        return False
