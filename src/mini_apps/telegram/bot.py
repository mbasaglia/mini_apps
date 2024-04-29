import re
import json
import time
import asyncio
import urllib.parse

import telethon
from telethon.sessions import MemorySession

from ..service import ServiceStatus, LogRetainingService
from ..apps.auth.user import clean_telegram_auth, User
from ..http.web_app import SocketService, JinjaApp, ServiceWithUserFilter
from .command import bot_command, BotCommand
from .events import NewMessageEvent, InlineQueryEvent, ChatActionEvent, CallbackQueryEvent
from . import tl


def meta_bot(name, bases, attrs):
    """
    Metaclass for telegram bot to allow automatic registration of commands from methods
    """
    bot_commands = {}
    for base in bases:
        base_commands = getattr(base, "_class_bot_commands", {})
        bot_commands.update(base_commands)

    for attr in attrs.values():
        command = getattr(attr, "bot_command", None)
        if command and isinstance(command, BotCommand):
            bot_commands[command.trigger] = command

    attrs["_class_bot_commands"] = bot_commands


class TelegramBot(LogRetainingService, ServiceWithUserFilter):
    """
    Contains boilerplate code to manage the various connections
    Inherit from this and override the relevant methods to implement your own bot
    """
    _class_bot_commands = {}
    command_trigger = re.compile(r"^/(?P<trigger>[a-zA-Z0-9_]+)(?:@(?P<username>[a-zA-Z0-9_]+))?\s?(?P<args>.*)", re.DOTALL)
    meta_processors = set([meta_bot])

    def __init__(self, settings):
        super().__init__(settings)
        self.telegram = None
        self.telegram_me = None
        self.token = self.settings["bot-token"]
        self.flood_end = 0
        self._bot_commands = None

    @property
    def bot_commands(self):
        if self._bot_commands is None:
            self._bot_commands = self.get_bot_commands()
        return self._bot_commands

    def get_bot_commands(self):
        return self._class_bot_commands

    async def info(self) -> dict:
        """
        Returns a dict of additional information about this bot (displayed on the admin page)
        """
        info = {}
        await self.get_info(info)
        return info

    async def get_info(self, info: dict):
        """
        Updates the info dict
        """
        pass

    def telegram_link(self):
        """
        Return the url for telegram
        """
        return "https://t.me/" + self.telegram_me.username

    def flood_left(self):
        if self.flood_end > 0:
            return round(self.flood_end - time.time())
        return 0

    def add_event_handlers(self):
        """
        Sets the telegram event handlers
        """
        self.telegram.add_event_handler(self.on_telegram_message_raw, telethon.events.NewMessage)
        self.telegram.add_event_handler(self.on_telegram_callback_raw, telethon.events.CallbackQuery)
        self.telegram.add_event_handler(self.on_telegram_inline_raw, telethon.events.InlineQuery)

    async def run(self):
        """
        Runs the telegram bot
        """
        try:
            self.status = ServiceStatus.Starting
            session = self.settings.get("session", MemorySession())
            api_id = self.settings["api-id"]
            api_hash = self.settings["api-hash"]

            self.telegram = telethon.TelegramClient(session, api_id, api_hash)
            dc = self.settings.get("telegram-server")
            if dc:
                self.telegram.session.set_dc(dc["dc"], dc["address"], dc["port"])
            self.add_event_handlers()

            while True:
                try:
                    await self.telegram.start(bot_token=self.token)
                    break
                except telethon.errors.rpcerrorlist.FloodWaitError as e:
                    self.status = ServiceStatus.StartFlood
                    self.log.warn("Wating for %ss (Flood Wait) %s", e.seconds, e)
                    self.flood_end = time.time() + e.seconds
                    await asyncio.sleep(e.seconds)
                    self.flood_end = 0

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

    async def stop(self):
        if self.telegram and self.telegram.is_connected():
            await self.telegram.disconnect()

    async def get_commands(self):
        """
        Returns the bot commands from the server
        """
        if not self.telegram or not self.telegram.is_connected():
            return None
        r = await self.telegram(telethon.functions.bots.GetBotCommandsRequest(
            tl.types.BotCommandScopeDefault(), "en"
        ))
        return r

    def gather_telegram_commands(self, scope, predicate):
        """
        Returns command objects to send to Telegram
        """
        commands = []
        for command in self.bot_commands.values():
            if predicate(command):
                commands.append(command.to_data())
        return commands

    async def send_telegram_commands(
        self,
        scope=tl.types.BotCommandScopeDefault(),
        predicate=(lambda cmd: not cmd.hidden and not cmd.admin_only)
    ):
        """
        Automatically sends the registered commands
        """
        commands = self.gather_telegram_commands(scope, predicate)

        await self.telegram(telethon.functions.bots.SetBotCommandsRequest(
            scope, "en", commands
        ))

    async def on_telegram_message_raw(self, event: NewMessageEvent):
        """
        Called on messages sent to the telegram bot
        wraps on_telegram_message() for convenience and detects bot /commands
        """
        try:
            self.log.debug("%s NewMessage %s", event.sender_id, event.text[:80])
            user = self.filter.filter_telegram_id(event.sender_id)
            event.bot_user = user
            if not user:
                self.log.debug("%s is banned", event.sender_id)
                return

            if not await self.should_process_event(event):
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

    async def should_process_event(self, event):
        """
        Used to filter events
        """
        return True

    async def on_telegram_command(self, trigger: str, args: str, event: NewMessageEvent):
        """
        Called on a telegram /command

        :return: True if the command has been handled
        """
        cmd = self.bot_commands.get(trigger)
        if cmd and (not cmd.admin_only or event.bot_user.is_admin):
            await cmd.function(self, args, event)
            return True

        return False

    async def on_telegram_callback_raw(self, event: CallbackQueryEvent):
        """
        Called on telegram callback queries (inline button presses),
        just wraps on_telegram_callback() with exception handling for convenience
        """
        try:
            event.bot_user = self.filter.filter_telegram_id(event.sender_id)
            if not event.bot_user:
                self.log.debug("%s is banned", event.sender_id)
                return
            await self.on_telegram_callback(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_telegram_inline_raw(self, event: InlineQueryEvent):
        """
        Called on telegram inline queries,
        just wraps on_telegram_inline() with exception handling for convenience
        """
        try:
            event.bot_user = self.filter.filter_telegram_id(event.sender_id)
            if not event.bot_user:
                self.log.debug("%s is banned", event.sender_id)
                await event.answer([])
                return
            await self.on_telegram_inline(event)
        except Exception as e:
            await self.on_telegram_exception(e)

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

    async def on_telegram_message(self, event: NewMessageEvent):
        """
        Called on messages sent to the telegram bot

        :returns: True if the message has been handled and needs no further processing
        """
        pass

    async def on_telegram_callback(self, event: CallbackQueryEvent):
        """
        Called on button presses on the telegram bot
        """
        pass

    async def on_telegram_inline(self, event: InlineQueryEvent):
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

    async def admin_log(self, message, *args, **kwargs):
        """
        Logs a bot administration message
        """
        self.log.info(message)


class TelegramMiniApp(TelegramBot, JinjaApp, SocketService):
    """
    Telegram bot with web frontend and socket connection
    """
    @property
    def runnable(self):
        return True

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the mini app initData
        Return None if authentication fails, otherwise return a user object
        """

        return self.user_from_data(message["data"])

    def user_from_data(self, data):
        data = self.decode_telegram_data(data)
        if data is None:
            fake_user = self.settings.get("fake-user")
            if fake_user:
                data = {"user": fake_user}
            else:
                return None

        user = User.from_telegram_dict(data["user"])
        user.telegram_data = data

        return user

    def decode_telegram_data(self, data: str):
        """
        Decodes data as per https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        """
        # Parse the data
        clean = {}
        for key, value in sorted(urllib.parse.parse_qs(data).items()):
            clean[key] = value[0]

        clean = clean_telegram_auth(clean, self.token, key_prefix=b"WebAppData")
        if clean is not None:
            clean["user"] = json.loads(clean["user"])

        return clean


class ChatActionsBot(TelegramBot):
    """
    Telegram bot that handles chat action events
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.join_shown = set()

    def add_event_handlers(self):
        super().add_event_handlers()
        self.telegram.add_event_handler(self.on_chat_action_raw, telethon.events.ChatAction)

    async def on_chat_action_raw(self, event: ChatActionEvent):
        """
        Called on telegram chat actions
        wraps on_chat_action() for convenience
        """
        try:
            await self.on_chat_action(event)
        except Exception as e:
            await self.on_telegram_exception(e)

    async def on_chat_action(self, event: ChatActionEvent):
        """
        Chat action handler
        """
        user = await event.get_user()
        chat = await event.get_chat()
        joined = event.user_joined or event.user_added
        left = event.user_kicked or event.user_left

        if self.telegram_me.id == user.id:
            if joined:
                await self.on_self_join(chat, event)
            elif left:
                await self.on_self_leave(chat, event)
        else:
            if joined:
                # Sometimes telegram sends two different events on user joins
                # Since you can't be guaranteed either of them is going to get sent, we cache recently joined user ids
                if user.id in self.join_shown:
                    return
                self.join_shown.add(user.id)
                await self.on_user_join(user, chat, event)
                await asyncio.sleep(1)
                self.join_shown.remove(user.id)
            elif left:
                await self.on_user_leave(user, chat, event)

    async def on_user_join(self, user, chat, event):
        """
        Called when a user (not the bot) joins a chat
        """

    async def on_self_join(self, chat, event):
        """
        Called when the bot joins a chat
        """

    async def on_user_leave(self, user, chat, event):
        """
        Called when a user (not the bot) leaves a chat
        """

    async def on_self_leave(self, chat, event):
        """
        Called when the bot leaves a chat
        """
