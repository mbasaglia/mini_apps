import asyncio
import json
import hmac
import hashlib
import importlib
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


class SettingsValue:
    """
    Object to access settings in a more convenient way than a dict
    """
    def __init__(self, data: dict = {}):
        for key, value in data.items():
            if isinstance(value, dict):
                value = SettingsValue(value)
            setattr(self, key.replace("-", "_"), value)

    def pop(self, key: str):
        """
        Removes a setting and returns its value
        """
        value = getattr(self, key)
        delattr(self, key)
        return value

    @classmethod
    def load(cls, filename, **extra):
        """
        Loads settings from a JSON file
        """
        with open(filename, "r") as settings_file:
            data = json.load(settings_file)
            data.update(extra)
            return cls(data)


class Settings(SettingsValue):
    """
    Global settings
    """
    def __init__(self, data: dict):
        database = data.pop("database")
        apps = data.pop("apps")
        super().__init__(data)

        self.database = self.load_database(database)
        self.apps = SettingsValue()
        self.app_list = []
        self.database_models = []

        for name, app_settings in apps.items():
            app = self.load_app(app_settings)
            setattr(self.apps, name, app)
            self.app_list.append(app)

    @classmethod
    def load_global(cls):
        """
        Loads the global settings file
        """
        server_path = pathlib.Path(__file__).absolute().parent.parent
        root = server_path.parent

        return cls.load(
            server_path / "settings.json",
            paths={
                "root": root,
                "server": server_path,
                "client": root / "client",
            }
        )

    def load_database(self, db_settings: dict):
        """
        Loads database settings
        """
        class_name = db_settings.pop("class")
        cls = getattr(peewee, class_name)

        if class_name == "SqliteDatabase":
            database_path = self.paths.root / db_settings["database"]
            database_path.parent.mkdir(parents=True, exist_ok=True)
            db_settings["database"] = str(database_path)

        return cls(**db_settings)

    def load_app(self, app_settings: dict):
        """
        Loads a mini app / bot
        """
        module_name, class_name = app_settings.pop("class").rsplit(".", 1)
        cls = getattr(importlib.import_module(module_name), class_name)
        app_settings.update(vars(self))
        settings = SettingsValue(app_settings)
        return cls(settings)

    def connect_database(self):
        """
        Connects to the database and initializes the models
        """
        database = connect(self.database)
        database.connect()
        database.create_tables(self.database_models)
        return database


class App:
    """
    Contains boilerplate code to manage the database and the web socket connections
    Inherit from this and override the relevant methods to implement your own app
    """

    def __init__(self, settings):
        self.clients = {}
        self.settings = settings
        self.telegram = None
        self.telegram_me = None

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

        with self.settings.database.atomic():
            user = User.get_user(data["user"])

        return user

    async def disconnect(self, client: Client):
        """
        Disconnects the given client
        """
        self.clients.pop(client.id)
        await self.on_client_disconnected(client)

    async def run_socket_server(self):
        """
        Runs the websocket server
        """
        self.on_server_start()

        host = self.settings.hostname
        port = self.settings.port

        async with websockets.serve(self.socket_handler, host, port):
            self.log("Connected as %s:%s" % (host, port))
            await asyncio.Future()  # run forever

    async def run_bot(self):
        """
        Runs the telegram bot
        """
        try:
            session = getattr(self.settings, "session", MemorySession())
            api_id = self.settings.api_id
            api_hash = self.settings.api_hash
            bot_token = self.settings.bot_token

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
        token = self.settings.bot_token.encode("ascii")
        secret_key = hmac.new(b"WebAppData", token, digestmod=hashlib.sha256).digest()
        correct_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        # If the hash is invalid, return None
        if clean.get("hash", "") != correct_hash:
            return None

        return clean

    def log(self, *args):
        print(self.__class__.__name__, *args)

    def register_models(self):
        """
        Override in derived classes to register the models in self.settings.database_models
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
