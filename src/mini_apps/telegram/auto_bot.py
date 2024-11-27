"""
Automatic command registration system

This functionality makes it easier to define a modular bot,
where multiple commands can be loaded from python functions in separate Python modules
"""
import sys
import pathlib
import importlib
import importlib.util

from .bot import TelegramBot
from .command import BotCommand
from .events import NewMessageEvent, CallbackQueryEvent, InlineQueryEvent


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
        self.loaded = {}
        self.current = None
        self.children = {}

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

    def load_module(self, module_name):
        if module_name in self.loaded:
            return self.loaded[module_name]

        data = AutoBotData()
        self.current = data
        self.loaded[module_name] = data
        importlib.import_module(module_name)
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

    def bot_command(self, trigger=None, description=None, hidden=False):
        """
        Registers a bot command handler
        """
        if callable(trigger):
            func = trigger
            trigger = None
        else:
            func = None

        def deco(func):
            command = BotCommand.from_function(func, trigger, description, hidden)
            if self.current:
                self.current.commands[command.trigger] = command
            return func

        if func is not None:
            return deco(func)

        return deco

    def bot_inline(self, func=None):
        """
        Registers a bot inline handler
        """
        def deco(func):
            if self.current:
                self.current.inline = func
            return func

        if func is not None:
            return deco(func)

        return deco

    def bot_button_callback(self, func=None):
        """
        Registers a bot button callback handler
        """
        def deco(func):
            if self.current:
                self.current.button_callback = func
            return func

        if func is not None:
            return deco(func)

        return deco

    def bot_media(self, func=None):
        """
        Registers a callback handler for messages containing media
        """
        def deco(func):
            if self.current:
                self.current.media = func
            return func

        if func is not None:
            return deco(func)

        return deco

    def child(self, name):
        if name in self.children:
            return self.children[name]

        br = AutoBotRegistry()
        br.current = AutoBotData()
        self.children[name] = br
        return br


class AutoBot(TelegramBot):
    """
    Bot that automatically loads commands from a directory
    """
    registry = AutoBotRegistry()

    def __init__(self, *args):
        super().__init__(*args)

        # Ensures we have an explicit name
        self.name = self.settings["name"]

        if self.settings.get("command-path"):
            path = pathlib.Path(self.settings["command-path"])
            if not path.exists():
                raise Exception("%s does not exist" % path)
            self.handlers = self.registry.load_path(path)
        elif self.settings.get("command-module"):
            self.handlers = self.registry.load_module(self.settings["command-module"])
        else:
            raise Exception("Missing `command-path` and `command-module`")

        # Allow filtering by name
        named = self.settings.get("named", None)
        if named:
            if isinstance(named, bool):
                named = self.name
            self.handlers = self.registry.child(named).current
        self._bot_commands = self.handlers.commands

    async def get_info(self, info: dict):
        await super().get_info(info)
        if "command-path" in self.settings:
            info["command-path"] = self.settings["command-path"]
        elif "command-module" in self.settings:
            info["command-module"] = self.settings["command-module"]

    async def on_telegram_callback(self, event: CallbackQueryEvent):
        if self.handlers.button_callback:
            await self.handlers.button_callback(self, event.query.data, event)

    async def on_telegram_inline(self, event: InlineQueryEvent):
        if self.handlers.inline:
            await self.handlers.inline(event)

    async def on_telegram_message(self, event: NewMessageEvent):
        if self.handlers.media and event.message.media and not event.sender.is_self:
            self.handlers.media(self, event)
            return True
        return False


# Expose global functions from the default registry
bot_command = AutoBot.registry.bot_command
bot_inline = AutoBot.registry.bot_inline
bot_button_callback = AutoBot.registry.bot_button_callback
bot_media = AutoBot.registry.bot_media


def bot(name):
    return AutoBot.registry.child(name)


def named_bot_command(name, *a, **kw):
    if a or kw:
        return bot(name).bot_command(*a, **kw)
    return bot(name).bot_command


def named_bot_inline(name):
    return bot(name).bot_inline


def named_bot_media(name):
    return bot(name).bot_media


def named_bot_button_callback(name):
    return bot(name).bot_button_callback
