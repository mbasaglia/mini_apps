import asyncio
import json
import hmac
import hashlib
import pathlib
import traceback
import urllib.parse

import peewee
import websockets

import telethon
from telethon.sessions import MemorySession

from .db import connect
from .models import User


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
    def __init__(self, database, settings, server_path, client_path):
        self.clients = {}
        self.database = database
        self.settings = settings
        self.telegram = None
        self.telegram_me = None
        self.server_path = server_path
        self.client_path = client_path

    async def socket_messages(self, client):
        """
        Generator that yields messages from the socket
        """
        async for message in client.socket:
            try:
                data = json.loads(message)
                yield data
            except Exception as e:
                self.log("Error", client.id, message)
                await self.on_socket_exception(client, e)

    async def socket_handler(self, socket):
        """
        Main entry point for socket connections
        """

        # Create the client object for this socket
        client = Client(socket)
        await client.send(type="connect")
        await self.on_client_connected(client)

        # Wait for a login message
        async for message in self.socket_messages(client):
            self.log(client.id, message)
            if message["type"] != "login":
                await client.send(type="error", msg="You need to login first")
            else:
                await self.login(client, message)
                break

        try:
            # Disconnect if there is no correct login
            if not client.user:
                await client.send(type="disconnect")
                await self.disconnect(client)
                return

            # Process messages from the client
            async for message in self.socket_messages(client):
                type = message.get("type", "")
                await self.handle_message(client, type, message)

        finally:
            # Disconnect when the client has finished
            await self.disconnect(client)

    async def login(self, client: Client, message: dict):
        """
        Login logic
        """
        client.user = self.get_user(message)
        self.clients[client.id] = client
        if client.user:
            await self.on_client_authenticated(client)

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the mini app initData
        Return None if authentication fails, otherwise return a user object
        """
        data = self.decode_telegram_data(message["data"])
        if data is None:
            return None

        with self.database.atomic():
            user = User.get_user(data["user"])

        return user

    async def disconnect(self, client: Client):
        """
        Disconnects the given client
        """
        self.clients.pop(client.id)
        await self.on_client_disconnected(client)

    async def run_socket_server(self, host: str, port: int):
        """
        Runs the websocket server
        """
        self.on_server_start()

        async with websockets.serve(self.socket_handler, host, port):
            self.log("Connected as %s:%s" % (host, port))
            await asyncio.Future()  # run forever

    async def run_bot(self, session, api_id: int, api_hash: str, bot_token: str):
        """
        Runs the telegram bot
        """
        try:
            self.telegram = telethon.TelegramClient(session, api_id, api_hash)
            self.telegram.add_event_handler(self.on_telegram_message_raw, telethon.events.NewMessage)
            self.telegram.add_event_handler(self.on_telegram_callback_raw, telethon.events.CallbackQuery)
            self.telegram.add_event_handler(self.on_telegram_inline_raw, telethon.events.InlineQuery)
            await self.telegram.start(bot_token=bot_token)
            self.telegram_me = await self.telegram.get_me()
            self.log("Telegram bot @%s" % self.telegram_me.username)
            await self.on_telegram_connected()
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_message_raw(self, event: telethon.events.NewMessage):
        """
        Called on messages sent to the telegram bot
        wraps on_telegram_message() for convenience and detects the /start message
        """
        try:
            if event.text.startswith("/start"):
                await self.on_telegram_start(event)
            else:
                await self.on_telegram_message(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_callback_raw(self, event: telethon.events.CallbackQuery):
        """
        Called on telegram callback queries (inline button presses),
        just wraps on_telegram_callback() with exception handling for convenience
        """
        try:
            await self.on_telegram_callback(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_inline_raw(self, event: telethon.events.InlineQuery):
        """
        Called on telegram inline queries,
        just wraps on_telegram_inline() with exception handling for convenience
        """
        try:
            await self.on_telegram_inline(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def run(self):
        """
        Runs the telegram bot and socket server
        """
        self.connect()

        try:
            self.init_database()

            run_app_task = asyncio.create_task(self.run_socket_server(
                self.settings["hostname"],
                self.settings["port"]
            ))
            run_bot_task = asyncio.create_task(self.run_bot(
                self.settings.get("session", MemorySession()),
                self.settings["api-id"],
                self.settings["api-hash"],
                self.settings["bot-token"]
            ))

            done, pending = await asyncio.wait(
                [run_app_task, run_bot_task],
                return_when=asyncio.ALL_COMPLETED
            )

            for task in pending:
                task.cancel()

        except KeyboardInterrupt:
            pass
        finally:
            self.database.close()

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

        return cls(database, settings, server_path, root / "client")

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

    def log(self, *args):
        print(self.__class__.__name__, *args)

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

    async def on_socket_exception(self, client: Client, exception: Exception):
        """
        Called when there is an exception while processing a socket message
        """
        traceback.print_exc()
        await client.send(type="error", msg=str(exception))

    async def on_telegram_exception(self, exception: Exception):
        """
        Called when there is an exception on the telegram connection
        """
        traceback.print_exc()

    async def on_telegram_connected(self):
        """
        Called when the connection to the telegram bot is established
        """
        pass

    async def on_telegram_start(self, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        pass

    async def on_telegram_message(self, event: telethon.events.NewMessage):
        """
        Called on messages sent to the telegram bot
        """
        pass

    async def on_telegram_callback(self, event: telethon.events.CallbackQuery):
        """
        Called on button presses on the telegram bot
        """
        pass

    async def on_telegram_inline(self, event: telethon.events.InlineQuery):
        """
        Called on telegram bot inline queries
        """
        pass
