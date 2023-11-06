import asyncio
import json

import aiohttp
import aiohttp.web
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from yarl import URL

from ..service import BaseService, ServiceStatus, Client, Service, ServiceProvider
from .middleware.csrf import CsrfMiddleware
from .utils import ExtendedApplication


class HttpServer(BaseService):
    """
    Class that runs the https server and dispatches incoming messages to the installed apps / routes
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.app = ExtendedApplication()
        self.middleware = [
            CsrfMiddleware(settings)
        ]
        aiohttp_session.setup(self.app, EncryptedCookieStorage(settings["secret-key"]))
        self.host = settings.get("host", "localhost")
        self.port = settings.get("port", 2537)
        self.http_provider = ServiceProvider("http", self)
        self.socket_provider = ServiceProvider("websocket", self)
        self.stop_future = None
        self.websocket_settings = settings.get("websocket", "")
        self.base_url = settings["url"].rstrip("/")
        self.websocket_url = self.base_url.replace("http", "ws") + self.websocket_settings
        self.common_template_paths = []
        if self.websocket_settings:
            self.app.add_routes([aiohttp.web.get(self.websocket_settings, self.socket_handler)])

    def url(self, url_name, *, app=None, **kwargs):
        router = (app or self.app).router
        for chunk in url_name.split(":"):
            resource = router.named_resources()[chunk]
            try:
                router = resource._app.router
            except Exception:
                break
        return URL(self.base_url + str(resource.url_for(**kwargs)))

    def register_consumer(self, what, service: Service):
        """
        Registeres a service
        """
        if what == "http":
            self.http_provider.register_app(service)
        elif what == "websocket":
            self.socket_provider.register_app(service)

    def register_middleware(self, middleware):
        self.middleware.append(middleware)

    async def run(self):
        """
        Runs the websocket server
        """
        self.status = ServiceStatus.Starting

        try:
            loop = asyncio.get_running_loop()
            self.stop_future = loop.create_future()

            for mid in self.middleware:
                self.app.middlewares.append(mid.process_request)

            self.http_provider.on_start()
            self.socket_provider.on_start()

            runner = aiohttp.web.AppRunner(self.app)
            await runner.setup()
            self.site = aiohttp.web.TCPSite(runner, self.host, self.port)
            await self.site.start()

            self.status = ServiceStatus.Running
            self.log.info("Connected as %s:%s", self.host, self.port)
            self.log.info("Public URL %s", self.base_url)
            # run until task is cancelled or until self.stop()
            await self.stop_future
            self.log.info("Stopped")
            self.status = ServiceStatus.Disconnected

            self.http_provider.on_stop()
            self.socket_provider.on_stop()

        except Exception:
            self.status = ServiceStatus.Crashed
            self.log_exception()

    async def stop(self):
        """
        Stops self.run()
        """
        if self.stop_future and not self.stop_future.cancelled():
            self.log.debug("Shutting down HTTP server")
            self.stop_future.set_result(None)
            await self.site.stop()

    async def socket_handler(self, request):
        """
        Main entry point for socket connections
        """
        socket = aiohttp.web.WebSocketResponse()
        await socket.prepare(request)

        # Log in and assign client to an app
        try:
            # Create the client object for this socket
            client = Client(socket)
            self.log.debug("#%s connected from %s", client.id, request.remote)
            await client.send(type="connect")

            # Wait for a login message
            async for app, message, raw in self.socket_messages(client):
                self.log.debug("#%s setup %s", client.id, raw[:80])
                if message["type"] != "login":
                    await client.send(type="error", msg="You need to login first")
                else:
                    client.app = app
                    try:
                        await app.login(client, message)
                    except Exception:
                        app.log_exception()
                        pass
                    break

            # Disconnect if there is no correct login
            if not client.app or not client.user:
                self.log.debug("#%s failed login", client.id)
                if not client.socket.closed:
                    await client.send(type="disconnect")
                return socket

        except Exception:
            self.log_exception()

        try:
            self.log.debug("#%s logged in as %s on %s", client.id, client.to_json(), app.name)
            await client.send(type="welcome", **client.to_json())
            await client.app.on_client_authenticated(client)

            # Process messages from the client
            async for app, message, raw in self.socket_messages(client):
                self.log.debug("#%s %s msg %s", client.id, app.name, raw[:80])
                type = message.get("type", "")
                await app.handle_message(client, type, message)

        except Exception:
            client.app.log_exception()

        finally:
            # Disconnect when the client has finished
            await client.app.disconnect(client)

        return socket

    async def socket_messages(self, client: Client):
        """
        Generator that yields messages from the socket
        """
        try:
            async for message in client.socket:
                if message.type == aiohttp.WSMsgType.ERROR:
                    await self.log.warn(str(client.socket.exception()))
                    return
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    return
                elif message.type != aiohttp.WSMsgType.TEXT:
                    continue

                try:
                    data = json.loads(message.data)
                    # Find the app this message is for
                    app_name = data.pop("app", None)
                    if app_name:
                        app = self.socket_provider.apps.get(app_name)
                        if app:
                            yield app, data, message.data
                            continue

                    self.log.warn("#%s unknown %s", client.id, message.data[:80])
                    await client.send(type="error", msg="Missing App ID")
                except Exception:
                    self.log_exception("#%s Socket Error %s", client.id, message.data[:80])
                    await client.send(type="error", msg="Internal server error")
        except (asyncio.exceptions.IncompleteReadError):
            return

    def provides(self):
        provides = ["http"]
        if self.websocket_settings:
            provides.append("websocket")
        return provides
