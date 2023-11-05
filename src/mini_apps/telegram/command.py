import inspect

from . import tl


class BotCommand:
    """
    Class bot command
    """
    def __init__(self, function, trigger, description, hidden, admin_only):
        self.function = function
        self.trigger = trigger
        self.description = description
        self.hidden = hidden
        self.admin_only = admin_only

    def __repr__(self):
        return "<BotCommand %r>" % (
            self.trigger,
        )

    def to_data(self):
        """
        Returns the telegram data for the command
        """
        return tl.types.BotCommand(
            self.trigger,
            self.description or self.trigger
        )

    @classmethod
    def from_function(cls, func, trigger, description=None, hidden=False, admin_only=False):
        """
        Constructs an instance, filling missing data based on function introspection
        """
        if trigger is None:
            trigger = func.__name__

        if description is None:
            description = inspect.getdoc(func) or ""

        return cls(func, trigger, description, hidden, admin_only)


def bot_command(*args, **kwargs):
    """
    Decorator that automatically marks functions as commands

    :param trigger: Command trigger
    :param description: Command description as shown in the bot menu
    """
    if len(args) == 1 and callable(args[0]):
        func = args[0]
        func.bot_command = BotCommand.from_function(func, None)
        return func

    trigger = kwargs.pop("trigger", None)
    if not trigger and len(args) > 0:
        trigger = args[0]
    description = kwargs.pop("description", None)
    hidden = kwargs.pop("hidden", False)
    admin_only = kwargs.pop("admin_only", False)

    def decorator(func):
        func.bot_command = BotCommand.from_function(func, trigger, description, hidden, admin_only)
        return func

    return decorator


def hidden_command(*args, **kwargs):
    """
    Decorator tagging hidden commands
    """
    kwargs["hidden"] = True
    return bot_command(*args, **kwargs)


def admin_command(*args, **kwargs):
    """
    Decorator tagging admin commands
    """
    kwargs["admin_only"] = True
    return bot_command(*args, **kwargs)
