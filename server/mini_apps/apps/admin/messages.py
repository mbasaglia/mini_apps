"""
Inspired by django.contrib.messages
"""

import dataclasses

DEBUG = "debug"
INFO = "info"
SUCCESS = "success"
WARNING = "warning"
ERROR = "error"

_REQUEST_KEY = "messages"


@dataclasses.dataclass
class Message:
    message: str
    level_tag: str

    @property
    def tags(self):
        return self.level_tag

    def __str__(self):
        return self.message


def add_message(request, level, message):
    if _REQUEST_KEY not in request:
        request[_REQUEST_KEY] = []

    request[_REQUEST_KEY].append(Message(message, level))
