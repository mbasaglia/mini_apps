"""
Automatic command registration system

This functionality makes it easier to define a modular bot,
where multiple commands can be loaded from python functions in separate Python modules
"""
import sys
import pathlib
import importlib.util

import telethon

from .bot import Bot
from .command import BotCommand


class AutoBotData:
    """
    Collection of bot event handlers
    """
    def __init__(self):
        self.commands = {}
        self.media = None
        self.inline = None
        self.button_callback = None

    def has_data(self):
        """
        Returns True if there is at least one registered handler
        """
        return self.commands or self.inline or self.media or self.button_callback


class AutoBotRegistry:
    """
    Keeps track of all the "auto" bot handlers
    """
    def __init__(self):
        self.bots = {}
        self.loaded = {}
        self.current = None

    def bot(self, username):
        if not username:
            return self.current

        bot = self.bots.get(username)
        if not bot:
            bot = AutoBotData()
            self.bots[username] = bot
        return bot

    def load_path(self, path: pathlib.Path):
        canonical = path.resolve()
        path_id = str(canonical)

        if path_id in self.loaded:
            return self.loaded[path_id]

        data = AutoBotData()
        self.current = data
        self.loaded[path_id] = data
        self._collect_path("_autobot", path)
        self.current = None
        return data

    def _module_from_file(self, name: str, path: pathlib.Path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def _collect_path(self, name: str, path: pathlib.Path):
        if path.suffix == ".py" and path.is_file():
            self._module_from_file(name + "." + path.stem, path)
        elif path.is_dir() and path.name != "__pycache__" and path.name != "assets":
            self._collect_files(name + "." + path.name, path)

    def _collect_files(self, name: str, path: pathlib.Path):
        for file in path.iterdir():
            self._collect_path(name, file)

    def bot_command(self, bot_username, trigger=None, description=None, hidden=False):
        """
        Registers a bot command handler
        """
        bot = self.bot(bot_username)

        def deco(func):
            command = BotCommand.from_function(trigger, description, hidden)
            bot.commands[command.trigger] = command
            return func

        return deco

    def bot_inline(self, bot_username):
        """
        Registers a bot inline handler
        """
        bot = self.bot(bot_username)

        def deco(func):
            bot.inline = func
            return func

        return deco

    def bot_button_callback(self, bot_username):
        """
        Registers a bot button callback handler
        """
        bot = self.bot(bot_username)

        def deco(func):
            bot.button_callback = func
            return func

        return deco

    def bot_media(self, bot_username):
        """
        Registers a callback handler for messages containing media
        """
        bot = self.bot(bot_username)

        def deco(func):
            bot.media = func
            return func

        return deco


class AutoBot(Bot):
    """
    Bot that automatically loads commands from a directory
    """
    registry = AutoBotRegistry()

    def __init__(self, *args):
        super().__init__(*args)
        if self.settings.command_path:
            self.handlers = self.self.registry.load_path(self.settings.command_path)
            if not self.handlers.has_data():
                self.handlers = None
        else:
            self.handlers = None

    async def on_telegram_connected(self):
        if not self.handlers:
            self.handlers = self.registry.bot(self.telegram_me.username)

    async def on_telegram_command(self, trigger: str, args: str, event: telethon.events.NewMessage):
        func = self.handlers.get(trigger)

        if func:
            await func(args, event)
            return True

        return False

    async def on_telegram_callback(self, event: telethon.events.CallbackQuery):
        if self.handlers.button_callback:
            await self.handlers.button_callback(event)

    async def on_telegram_inline(self, event: telethon.events.CallbackQuery):
        if self.handlers.inline:
            await self.handlers.inline(event)

    async def on_telegram_message(self, event: telethon.events.NewMessage):
        if self.handlers.media and event.message.media and not event.sender.is_self:
            self.handlers.media(event)


# Expose global functions from the default registry
bot_command = AutoBot.registry.bot_command
bot_inline = AutoBot.registry.bot_inline
bot_button_callback = AutoBot.registry.bot_button_callback
bot_media = AutoBot.registry.bot_media
