import aiohttp.web
from ...service import Service, ServiceStatus


class Middleware(Service):
    def __init__(self, settings):
        super().__init__(settings)
        self.http = None

    @property
    def runnable(self):
        return False

    async def run(self):
        self.status = ServiceStatus.Running

    def consumes(self):
        return super().consumes() + ["http"]

    def on_provider_added(self, provider):
        super().on_provider_added(provider)
        if provider.name == "http":
            self.http = provider.service
            self.http.middleware.append(self)

    @aiohttp.web.middleware
    async def process_request(self, request: aiohttp.web.Request, handler):
        """
        aiohttp middleware
        """
        return await self.on_process_request(request, handler)

    async def on_process_request(self, request: aiohttp.web.Request, handler):
        """
        Request processing implementation
        """
        return await handler(request)

    async def process_context(self, request: aiohttp.web.Request):
        """
        Jinja2 middleware
        """
        return await self.on_process_context(request)

    async def on_process_context(self, request: aiohttp.web.Request):
        """
        Jinja2 context processing implementation
        """
        return {}
