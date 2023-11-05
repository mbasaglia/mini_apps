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
    def add_static_path(self, prefix, path: pathlib.Path):
        """
        Registers a static path to the app
        """
        if path.is_file():
            self.router.register_resource(FileResource(prefix, path))
        else:
            self.router.add_static(prefix, path)

    def add_named_subapp(self, name, app: aiohttp.web.Application):
        # Work around aiohttp add_aubapp so we can set the subapp name
        resource = aiohttp.web.PrefixedSubAppResource("/%s" % name, app)
        resource._name = name
        self.router.register_resource(resource)
        self._reg_subapp_signals(app)
        self._subapps.append(app)
        app.pre_freeze()
