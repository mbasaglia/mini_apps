import asyncio
import json

import websockets

from .service import Service


class AutoId:
    """
    Class that automatically assigns an incrementing ID on construction
    """
    _next_id = 0

    def __init__(self):
        self.id = self.get_id()

    @classmethod
    def get_id(cls):
        id = cls._next_id
        cls._next_id += 1
        return id


class Client(AutoId):
    """
    Client object, contains a socket for the connection and a user for data
    """
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.user = None
        self.app = None

    async def send(self, **data):
        await self.socket.send(json.dumps(data))

    def to_json(self):
        return self.user.to_json()


class WebsocketServer(Service):
    """
    Class that runs the websocket server and dispatches incoming messages to
    the installed apps
    """

    def __init__(self, host, port, apps):
        super().__init__("socket")
        self.host = host
        self.port = port
        self.apps = apps
        self.stop_future = None

    async def socket_messages(self, client: Client):
        """
        Generator that yields messages from the socket
        """
        try:
            async for message in client.socket:
                try:
                    data = json.loads(message)
                    # Find the app this message is for
                    app_name = data.pop("app", None)
                    if app_name:
                        app = getattr(self.apps, app_name, None)
                        if app:
                            yield app, data, message
                            continue

                    self.log.warn("#%s unknown %s", client.id, message)
                    await client.send(type="error", msg="Missing App ID")
                except Exception:
                    self.log_exception("Socket Error", client.id, message)

                    await client.send(type="error", msg="Internal server error")
        except (asyncio.exceptions.IncompleteReadError, websockets.exceptions.ConnectionClosedError):
            return

    async def socket_handler(self, socket):
        """
        Main entry point for socket connections
        """

        # Create the client object for this socket
        client = Client(socket)
        self.log.debug("#%s connected from %s", client.id, socket.host)
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
            if client.socket.open:
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

    async def run(self):
        """
        Runs the websocket server
        """
        loop = asyncio.get_running_loop()
        self.stop_future = loop.create_future()

        for app in vars(self.apps).values():
            app.on_server_start()

        async with websockets.serve(self.socket_handler, self.host, self.port):
            self.log.info("Connected as %s:%s" % (self.host, self.port))
            # run until task is cancelled or until self.stop()
            await self.stop_future
            self.log.info("Stopped")

    def stop(self):
        """
        Stops self.run()
        """
        if not self.stop_future.cancelled:
            self.stop_future.set_result(None)
