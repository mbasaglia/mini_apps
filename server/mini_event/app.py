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
    _next_id = 0

    def __init__(self):
        self.id = self.get_id()

    @classmethod
    def get_id(cls):
        id = cls._next_id
        cls._next_id += 1
        return id


class Client(AutoId):
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.user = None

    async def send(self, **data):
        await self.socket.send(json.dumps(data))

    def to_json(self):
        return {"id": self.user.id, "telegram_id": self.user.telegram_id}


class App:
    def __init__(self, database, settings):
        self.clients = {}
        self.database = database
        self.settings = settings

    def atomic(self):
        return self.database.atomic()

    async def socket_messages(self, client):
        async for message in client.socket:
            try:
                data = json.loads(message)
                yield data
            except Exception as e:
                print(message)
                print(traceback.print_exc())
                await client.send(type="error", msg=str(e))

    async def socket_handler(self, socket):
        client = Client(socket)
        await client.send(type="connect")
        await self.on_client_connected(client)

        async for message in self.socket_messages(client):
            print(client.id, message)
            if message["type"] != "login":
                await client.send(type="error", msg="You need to login first")
            else:
                await self.login(client, message)
                break

        if not client.user:
            await self.disconnect(client)
            return

        async for message in self.socket_messages(client):
            type = message.get("type", "")
            print(client.id, message)
            await self.handle(client, type, message)

        await self.disconnect(client)

    async def login(self, client: Client, message: dict):
        client.user = self.get_user(message)
        self.clients[client.id] = client
        if client.user:
            await self.on_client_authenticated(client)

    async def disconnect(self, client: Client):
        self.clients.pop(client.id)
        await self.on_client_disconnected(client)

    async def run(self, host: str, port: int):
        self.init_database()

        async with websockets.serve(self.socket_handler, host, port):
            print("Connected as %s:%s" % (host, port))
            await asyncio.Future()  # run forever

    @classmethod
    def from_settings(cls):
        server_path = pathlib.Path(__file__).absolute().parent.parent
        root = server_path.parent

        with open(server_path / "settings.json", "r") as settings_file:
            settings = json.load(settings_file)

        database_path = root / settings["database"]
        database_path.parent.mkdir(parents=True, exist_ok=True)

        database = peewee.SqliteDatabase(str(database_path))

        return cls(database, settings)

    def decode_telegram_data(self, data: str):
        clean = {}
        data_check_string = ""
        for key, value in sorted(urllib.parse.parse_qs(data).items()):
            if key == "user":
                clean[key] = json.loads(value[0])
            else:
                clean[key] = value[0]

            if key != "hash":
                data_check_string += "%s=%s\n" % (key, value[0])


        data_check_string = data_check_string.strip()
        token = self.settings["bot-token"].encode("ascii")
        secret_key = hmac.new(b"WebAppData", token, digestmod=hashlib.sha256).digest()
        correct_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        if clean.get("hash", "") != correct_hash:
            return None

        return clean

    def connect(self):
        return connect(self.database)

    def init_database(self):
        """
        Override in derived classes to register the models
        """
        pass

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the message from the socket
        Return None if authentication fails, otherwise return a user object
        """
        return None

    async def handle(self, client: Client, type: str, data: dict):
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
