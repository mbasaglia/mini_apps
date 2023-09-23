import asyncio
import json
import hmac
import hashlib
import pathlib
import urllib.parse


import peewee
import websockets

from .db import connect


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

    async def send(self, **data):
        await self.socket.send(json.dumps(data))

    def to_json(self):
        return self.user.to_json()


class App:
    """
    Contains boilerplate code to manage the database and the web socket connections
    Inherit from this and override the relevant methods to implement your own app
    """
    def __init__(self, database, settings):
        self.clients = {}
        self.database = database
        self.settings = settings

    async def socket_messages(self, client):
        """
        Generator that yields messages from the socket
        """
        async for message in client.socket:
            try:
                data = json.loads(message)
                yield data
            except Exception as e:
                await self.on_exception(client, e)

    async def socket_handler(self, socket):
        """
        Main entry point for socket connections
        """

        # Create the client object for this socket
        client = Client(socket)
        await self.on_client_connected(client)

        # Wait for a login message
        async for message in self.socket_messages(client):
            print(client.id, message)
            if message["type"] != "login":
                await client.send(type="error", msg="You need to login first")
            else:
                await self.login(client, message)
                break

        # Disconnect if there is no correct login
        if not client.user:
            await client.send(type="disconnect")
            await self.disconnect(client)
            return

        # Process messages from the client
        async for message in self.socket_messages(client):
            type = message.get("type", "")
            await self.handle_message(client, type, message)

        # Disconnect if the client has finished
        await self.disconnect(client)

    async def login(self, client: Client, message: dict):
        """
        Login logic
        """

        # Get the user object from the login data
        client.user = self.get_user(message)
        self.clients[client.id] = client
        if client.user:
            await self.on_client_authenticated(client)

    async def disconnect(self, client: Client):
        """
        Disconnects the given client
        """
        self.clients.pop(client.id)
        await self.on_client_disconnected(client)

    async def run(self, host: str, port: int):
        """
        Runs the server
        """
        self.init_database()
        self.on_server_start()

        async with websockets.serve(self.socket_handler, host, port):
            print("Connected as %s:%s" % (host, port))
            await asyncio.Future()  # run forever

    @classmethod
    def from_settings(cls):
        """
        Constructs an instance by loading the settings file
        """
        server_path = pathlib.Path(__file__).absolute().parent.parent
        root = server_path.parent

        with open(server_path / "settings.json", "r") as settings_file:
            settings = json.load(settings_file)

        database_path = root / settings["database"]
        database_path.parent.mkdir(parents=True, exist_ok=True)

        database = peewee.SqliteDatabase(str(database_path))

        return cls(database, settings)

    def decode_telegram_data(self, data: str):
        """
        Decodes data as per https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        """
        # Parse the data
        clean = {}
        data_check_string = ""
        for key, value in sorted(urllib.parse.parse_qs(data).items()):
            if key == "user":
                clean[key] = json.loads(value[0])
            else:
                clean[key] = value[0]

            if key != "hash":
                data_check_string += "%s=%s\n" % (key, value[0])

        # Check the hash
        data_check_string = data_check_string.strip()
        token = self.settings["bot-token"].encode("ascii")
        secret_key = hmac.new(b"WebAppData", token, digestmod=hashlib.sha256).digest()
        correct_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        # If the hash is invalid, return None
        if clean.get("hash", "") != correct_hash:
            return None

        return clean

    def connect(self):
        """
        Connects to the database
        """
        return connect(self.database)

    def init_database(self):
        """
        Override in derived classes to register the models
        """
        pass

    def on_server_start(self):
        """
        Called when the server starts
        """
        pass

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the message from the socket
        Return None if authentication fails, otherwise return a user object
        """
        return None

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Override to handle socket messages
        """
        pass

    async def on_client_connected(self, client: Client):
        """
        Called when a client connects to the server (before authentication)
        """
        pass

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        pass

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        pass

    async def on_exception(self, client: Client, exception: Exception):
        """
        Called when there is an exception while processing a message
        """
        print(message)
        print(traceback.print_exc())
        await client.send(type="error", msg=str(exception))
