import aiohttp.web


class Middleware:
    def __init__(self, http):
        self.http = http

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
