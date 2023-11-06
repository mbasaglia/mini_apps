import aiohttp

from .base import Middleware


class HeaderMiddleware(Middleware):
    def set_headers(self, response):
        for header, value in self.settings["headers"].items():
            response.headers[header.replace("_", "-")] = str(value)

    async def on_process_request(self, request: aiohttp.web.Request, handler):
        """
        Request processing implementation
        """
        try:
            resp: aiohttp.web.Response = await handler(request)
            self.set_headers(resp)
            return resp
        except Exception as e:
            if isinstance(e, aiohttp.web.Response):
                self.set_headers(e)
            raise
