import inspect

import telethon


class BotCommand:
    """
    Class bot command
    """
    def __init__(self, trigger, description, function, hidden):
        self.trigger = trigger
        self.description = description
        self.function = function
        self.hidden = hidden

    def __repr__(self):
        return "<BotCommand %r>" % (
            self.trigger,
        )

    def to_data(self):
        """
        Returns the telegram data for the command
        """
        return telethon.tl.types.BotCommand(
            self.trigger,
            self.description or self.trigger
        )


def bot_command(*args, **kwargs):
    """
    Decorator that automatically marks functions as commands

    :param trigger: Command trigger
    :param description: Command description as shown in the bot menu
    """
    if len(args) == 1 and callable(args[0]):
        func = args[0]
        trigger = func.__name__
        description = inspect.getdoc(func) or ""
        func.bot_command = BotCommand(trigger, description, func, False)
        return func

    trigger = kwargs.pop("trigger", None) or args[0]
    description = kwargs.pop("description", None)
    hidden = kwargs.pop("description", False)

    def decorator(func):
        desc = description
        if desc is None:
            desc = inspect.getdoc(func) or ""

        func.bot_command = BotCommand(trigger, desc, func, hidden)
        return func

    return decorator
