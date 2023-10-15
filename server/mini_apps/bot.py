import asyncio
import json
import hmac
import hashlib
import re
import urllib.parse

import telethon
from telethon.sessions import MemorySession

from .models import User
from .service import SocketService, ServiceStatus
from .command import bot_command, BotCommand


class MetaBot(type):
    """
    Metaclass for telegram bot to allow automatic registration of commands from methods
    """
    def __new__(cls, name, bases, attrs):
        bot_commands = {}
        for base in bases:
            base_commands = getattr(base, "bot_commands", {})
            bot_commands.update(base_commands)

        for attr in attrs.values():
            command = getattr(attr, "bot_command", None)
            if command and isinstance(command, BotCommand):
                bot_commands[command.trigger] = command

        attrs["bot_commands"] = bot_commands

        return super().__new__(cls, name, bases, attrs)


class Bot(SocketService, metaclass=MetaBot):
    """
    Contains boilerplate code to manage the various connections
    Inherit from this and override the relevant methods to implement your own app
    """
    bot_commands = {}
    command_trigger = re.compile(r"^/(?P<trigger>[a-zA-Z0-9_]+)(?:@(?P<username>[a-zA-Z0-9_]+))?(?P<args>.*)")

    def __init__(self, settings, name=None):
        super().__init__(settings, name)
        self.telegram = None
        self.telegram_me = None

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the mini app initData
        Return None if authentication fails, otherwise return a user object
        """
        data = self.decode_telegram_data(message["data"])
        if data is None:
            fake_user = self.settings.get("fake-user")
            if fake_user:
                data = {"user": fake_user.dict()}
            else:
                return None

        with self.settings.database.atomic():
            user = User.get_user(data["user"])
            user.telegram_data = data

        return user

    async def run(self):
        """
        Runs the telegram bot
        """
        try:
            self.status = ServiceStatus.Starting
            session = self.settings.get("session", MemorySession())
            api_id = self.settings.api_id
            api_hash = self.settings.api_hash
            bot_token = self.settings.bot_token

            self.telegram = telethon.TelegramClient(session, api_id, api_hash)
            dc = self.settings.get("telegram_server")
            if dc:
                self.telegram.session.set_dc(dc.dc, dc.address, dc.port)
            self.telegram.add_event_handler(self.on_telegram_message_raw, telethon.events.NewMessage)
            self.telegram.add_event_handler(self.on_telegram_callback_raw, telethon.events.CallbackQuery)
            self.telegram.add_event_handler(self.on_telegram_inline_raw, telethon.events.InlineQuery)

            while True:
                try:
                    await self.telegram.start(bot_token=bot_token)
                    break
                except telethon.errors.rpcerrorlist.FloodWaitError as e:
                    self.status = ServiceStatus.StartFlood
                    self.log.warn("Wating for %ss (Flood Wait)", e.seconds)
                    await asyncio.sleep(e.seconds)

            self.status = ServiceStatus.Starting

            self.telegram_me = await self.telegram.get_me()
            self.log.info("Telegram bot @%s", self.telegram_me.username)

            self.status = ServiceStatus.Running
            await self.on_telegram_connected()

            await self.send_telegram_commands()

            await self.telegram.disconnected
            self.status = ServiceStatus.Disconnected
        except Exception as e:
            self.status = ServiceStatus.Crashed
            await self.on_telegram_exception(e)

    async def send_telegram_commands(self):
        """
        Automatically sends the registered commands
        """
        commands = []
        for command in self.bot_commands.values():
            if not command.hidden:
                commands.append(command.to_data())

        await self.telegram(telethon.functions.bots.SetBotCommandsRequest(
            telethon.tl.types.BotCommandScopeDefault(), "en", commands
        ))

    async def on_telegram_message_raw(self, event: telethon.events.NewMessage):
        """
        Called on messages sent to the telegram bot
        wraps on_telegram_message() for convenience and detects bot /commands
        """
        try:
            self.log.debug("%s NewMessage %s", event.sender_id, event.text[:80])
            if not self.filter.filter_telegram_id(event.sender_id):
                self.log.debug("%s is banned", event.sender_id)
                return
            match = self.command_trigger.match(event.text)
            if match:
                username = match.group("username")
                if not username or username == self.telegram_me.username:
                    trigger = match.group("trigger")
                    args = match.group("args")
                    if await self.on_telegram_command(trigger, args, event):
                        return

            await self.on_telegram_message(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_command(self, trigger: str, args: str, event: telethon.events.NewMessage):
        """
        Called on a telegram /command

        :return: True if the command has been handled
        """
        cmd = self.bot_commands.get(trigger)
        if cmd:
            await cmd.function(self, args, event)
            return True

        return False

    async def on_telegram_callback_raw(self, event: telethon.events.CallbackQuery):
        """
        Called on telegram callback queries (inline button presses),
        just wraps on_telegram_callback() with exception handling for convenience
        """
        try:
            if not self.filter.filter_telegram_id(event.sender_id):
                self.log.debug("%s is banned", event.sender_id)
                return
            await self.on_telegram_callback(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_inline_raw(self, event: telethon.events.InlineQuery):
        """
        Called on telegram inline queries,
        just wraps on_telegram_inline() with exception handling for convenience
        """
        try:
            if not self.filter.filter_telegram_id(event.sender_id):
                self.log.debug("%s is banned", event.sender_id)
                return
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

    async def on_telegram_exception(self, exception: Exception):
        """
        Called when there is an exception on the telegram connection
        """
        self.log_exception("Telegram Error")

    async def on_telegram_connected(self):
        """
        Called when the connection to the telegram bot is established
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

    @staticmethod
    def bot_command(*args, **kwargs):
        """
        Decorator that automatically registers methods as commands

        :param trigger: Command trigger
        :param description: Command description as shown in the bot menu
        """
        return bot_command(*args, **kwargs)
