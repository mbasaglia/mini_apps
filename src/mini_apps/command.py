import inspect

import telethon


class BotCommand:
    """
    Class bot command
    """
    def __init__(self, function, trigger, description, hidden):
        self.function = function
        self.trigger = trigger
        self.description = description
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

    @classmethod
    def from_function(cls, func, trigger, description, hidden):
        """
        Constructs an instance, filling missing data based on function introspection
        """
        if trigger is None:
            trigger = func.__name__

        if description is None:
            description = inspect.getdoc(func) or ""

        return cls(func, trigger, description, hidden)


def bot_command(*args, **kwargs):
    """
    Decorator that automatically marks functions as commands

    :param trigger: Command trigger
    :param description: Command description as shown in the bot menu
    """
    if len(args) == 1 and callable(args[0]):
        func = args[0]
        func.bot_command = BotCommand.from_function(func, None, None, False)
        return func

    trigger = kwargs.pop("trigger", None)
    if not trigger and len(args) > 0:
        trigger = args[0]
    description = kwargs.pop("description", None)
    hidden = kwargs.pop("description", False)

    def decorator(func):
        func.bot_command = BotCommand.from_function(func, trigger, description, hidden)
        return func

    return decorator
