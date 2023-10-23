"""
Inspired by django.contrib.messages
"""

import dataclasses

import aiohttp_session

from .base import Middleware

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
    rendered: bool = False

    @property
    def tags(self):
        return self.level_tag

    def __str__(self):
        return self.message

    def render(self):
        self.rendered = True
        return self.message

    def to_json(self):
        return vars(self)

    @classmethod
    def from_json(cls, data):
        return cls(**data)


def add_message(request, level, message):
    if _REQUEST_KEY not in request:
        request[_REQUEST_KEY] = []

    request[_REQUEST_KEY].append(Message(message, level))


class MessageMiddleware(Middleware):
    async def on_process_request(self, request, handler):
        session = await aiohttp_session.get_session(request)
        request[_REQUEST_KEY] = list(map(Message.from_json, session.get(_REQUEST_KEY, [])))
        response = await handler(request)
        session[_REQUEST_KEY] = [m.to_json() for m in request[_REQUEST_KEY] if not m.rendered]
        return response

    async def on_process_context(self, request):
        return {
            "messages": request[_REQUEST_KEY],
        }
