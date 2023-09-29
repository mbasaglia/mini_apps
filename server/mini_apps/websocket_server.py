import asyncio
import json

import websockets

from .settings import LogSource


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


class WebsocketServer(LogSource):
    """
    Class that runs the websocket server and dispatches incoming messages to
    the installed apps
    """

    def __init__(self, host, port, apps, log):
        super().__init__("socket", log)
        self.host = host
        self.port = port
        self.apps = apps
        self.stop_future = None

    async def socket_messages(self, client: Client):
        """
        Generator that yields messages from the socket
        """
        async for message in client.socket:
            try:
                data = json.loads(message)
                # Find the app this message is for
                app_name = data.pop("app", None)
                if app_name:
                    app = getattr(self.apps, app_name, None)
                    if app:
                        yield app, data
                        continue

                self.log("Unknown Message", client.id, message)
                await client.send(type="error", msg="Missing App ID")
            except Exception:
                self.log_exeption("Socket Error", client.id, message)

                await client.send(type="error", msg="Internal server error")

    async def socket_handler(self, socket):
        """
        Main entry point for socket connections
        """

        # Create the client object for this socket
        client = Client(socket)
        self.log("#%s connected from %s" % (client.id, socket.host))
        await client.send(type="connect")

        # Wait for a login message
        async for app, message in self.socket_messages(client):
            if message["type"] != "login":
                await client.send(type="error", msg="You need to login first")
            else:
                client.app = app
                await app.login(client, message)
                break

        # Disconnect if there is no correct login
        if not client.app or not client.user:
            await client.send(type="disconnect")
            return

        try:
            await client.send(type="welcome", **client.to_json())
            await client.app.on_client_authenticated(client)

            # Process messages from the client
            async for app, message in self.socket_messages(client):
                type = message.get("type", "")
                await app.handle_message(client, type, message)

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
            self.log("Connected as %s:%s" % (self.host, self.port))
            await self.stop_future # run forever (or until stop)
            self.log("Stopped")

    def stop(self):
        self.stop_future.set_result(None)
