import aiohttp

from .base import Middleware
from ..service import Service, ServiceStatus



class HeaderMiddleware(Service, Middleware):
    def __init__(self, settings):
        Service.__init__(self, settings)
        Middleware.__init__(self, None)

    def on_provider_added(self, provider):
        super().on_provider_added(provider)
        if provider.name == "http":
            self.http = provider.service
            self.http.register_middleware(self)

    @property
    def runnable(self):
        return False

    async def run(self):
        self.status = ServiceStatus.Running


    async def on_process_request(self, request: aiohttp.web.Request, handler):
        """
        Request processing implementation
        """
        resp: aiohttp.web.Response = await handler(request)
        for header, value in self.settings.headers.dict().items():
            resp.headers[header.replace("_", "-")] = str(value)

        return resp

    def consumes(self):
        return super().consumes() + ["http"]
