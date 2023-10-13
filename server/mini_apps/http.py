import asyncio
import json

import aiohttp
import aiohttp.web
import aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from .service import BaseService, ServiceStatus, Client
from .middleware import Middleware
from .middleware.csrf import CsrfMiddleware



class HttpServer(BaseService):
    """
    Class that runs the https server and dispatches incoming messages to the installed apps / routes
    """

    def __init__(self, host, port, settings):
        super().__init__("http", settings)
        self.app = aiohttp.web.Application()
        self.middleware = [
            CsrfMiddleware()
        ]
        aiohttp_session.setup(self.app, settings.server.secret_key)
        for mid in self.middleware:
            self.app.middlewares.append(mid.process_request)
        self.host = host
        self.port = port
        self.apps = {}
        self.stop_future = None
        self.websocket_settings = settings.server.get("websocket")
        self.client_path = settings.get("client-path", settings.paths.client)

    def register_routes(self):
        """
        Registers built-in routes
        """
        if self.websocket_settings:
            self.app.add_routes([aiohttp.web.get(self.websocket_settings, self.socket_handler)])

        self.app.add_routes([aiohttp.web.get("/settings.json", self.client_settings)])

        if self.client_path:
            self.app.router.add_static("/", self.client_path)

    def register_service(self, bot):
        """
        Registeres a bot
        """
        self.apps[bot.name] = bot
        bot.add_routes(self)

    async def run(self):
        """
        Runs the websocket server
        """
        self.status = ServiceStatus.Starting

        try:
            loop = asyncio.get_running_loop()
            self.stop_future = loop.create_future()

            for app in self.apps.values():
                app.on_server_start()

            runner = aiohttp.web.AppRunner(self.app)
            await runner.setup()
            self.site = aiohttp.web.TCPSite(runner, self.host, self.port)
            await self.site.start()

            self.status = ServiceStatus.Running
            self.log.info("Connected as %s:%s" % (self.host, self.port))
            # run until task is cancelled or until self.stop()
            await self.stop_future
            self.log.info("Stopped")
            self.status = ServiceStatus.Disconnected
        except Exception:
            self.status = ServiceStatus.Crashed
            self.log_exception()

    def add_static_web_app(self, bot, path):
        """
        Shorthand for serving a directory and its index.html for a web app
        """
        app = aiohttp.web.Application()
        app.router.add_get("/", self.file_handler(path / "index.html"))
        app.router.add_static("/", path)
        self.app.add_subapp("/%s" % bot.name, app)

    @staticmethod
    def file_handler(path):
        """
        Handler for the given file
        """
        async def handler(request):
            return aiohttp.web.FileResponse(path)
        return handler

    async def stop(self):
        """
        Stops self.run()
        """
        if self.stop_future and not self.stop_future.cancelled:
            self.stop_future.set_result(None)
            await self.site.stop()

    async def socket_handler(self, request):
        """
        Main entry point for socket connections
        """
        socket = aiohttp.web.WebSocketResponse()
        await socket.prepare(request)

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
            return

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
                        app = self.apps.get(app_name)
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

    async def client_settings(self, request):
        return aiohttp.web.json_response(self.settings.client.dict())
