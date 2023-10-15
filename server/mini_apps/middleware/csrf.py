"""
Simplified version of https://github.com/bitnom/aiohttp-csrf which is currently unmaintained
"""
import hmac
import uuid
import functools

import aiohttp.web
from aiohttp_session import get_session
from .base import Middleware


MIDDLEWARE_SKIP_PROPERTY = 'csrf_middleware_skip'
UNPROTECTED_HTTP_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')
REQUEST_NEW_TOKEN_KEY = 'aiohttp_csrf_new_token'
HEADER_NAME = FORM_FIELD_NAME = SESSION_KEY = "csrf_token"


class Storage():
    def _generate_token(self):
        return uuid.uuid4().hex

    async def generate_new_token(self, request):
        if REQUEST_NEW_TOKEN_KEY in request:
            return request[REQUEST_NEW_TOKEN_KEY]

        token = self._generate_token()

        request[REQUEST_NEW_TOKEN_KEY] = token

        return token

    async def _get(self, request):
        session = await get_session(request)
        return session.get(SESSION_KEY, None)

    async def get_token(self, request):
        token = await self._get(request)

        await self.generate_new_token(request)

        return token

    async def _save_token(self, request, response, token):
        session = await get_session(request)
        session[SESSION_KEY] = token

    async def save_token(self, request, response):
        old_token = await self._get(request)

        if REQUEST_NEW_TOKEN_KEY in request:
            token = request[REQUEST_NEW_TOKEN_KEY]
        elif old_token is None:
            token = await self.generate_new_token(request)
        else:
            token = None

        if token is not None:
            await self._save_token(request, response, token)


async def form_check(self, request, original_value):
    get = request.match_info.get(FORM_FIELD_NAME, None)
    post_req = await request.post() if get is None else None
    post = post_req.get(FORM_FIELD_NAME) if post_req is not None else None
    post = post if post is not None else ''
    token = get if get is not None else post

    return hmac.compare_digest(token, original_value)


async def header_check(self, request, original_value):
    token = request.headers.get(HEADER_NAME)
    return hmac.compare_digest(token, original_value)


async def form_or_header_check(request, original_value):
    if await header_check(request, original_value):
        return True

    if await form_check(request, original_value):
        return True

    return False


storage = Storage()


async def _check(request):
    if not isinstance(request, aiohttp.web.Request):
        raise RuntimeError('Can\'t get request from handler params')

    original_token = await storage.get_token(request)
    return await form_or_header_check(request, original_token)


def csrf_protect(handler=None):
    def wrapper(handler):
        @functools.wraps(handler)
        async def wrapped(*args, **kwargs):
            request = args[-1]

            if isinstance(request, aiohttp.web.View):
                request = request.request

            if (
                request.method not in UNPROTECTED_HTTP_METHODS
                and not await _check(request)
            ):
                raise aiohttp.web.HTTPForbidden(reason="csrf token mismatch")

            raise_response = False

            try:
                response = await handler(*args, **kwargs)
            except aiohttp.web.HTTPException as exc:
                response = exc
                raise_response = True

            if isinstance(response, aiohttp.web.Response):
                await storage.save_token(request, response)

            if raise_response:
                raise response

            return response

        setattr(wrapped, MIDDLEWARE_SKIP_PROPERTY, True)

        return wrapped

    if handler is None:
        return wrapper

    return wrapper(handler)


def csrf_exempt(handler):
    @functools.wraps(handler)
    async def wrapped_handler(*args, **kwargs):
        return await handler(*args, **kwargs)

    setattr(wrapped_handler, MIDDLEWARE_SKIP_PROPERTY, True)

    return wrapped_handler


@aiohttp.web.middleware
async def csrf_middleware(request, handler):
    if not getattr(handler, MIDDLEWARE_SKIP_PROPERTY, False):
        handler = csrf_protect(handler=handler)

    return await handler(request)


class CsrfMiddleware(Middleware):
    async def on_process_request(self, request, handler):
        return await csrf_middleware(request, handler)

    async def on_process_context(self, request):
        token = await storage.get_token(request)
        return {
            "csrf_token": token,
            "csrf": "<input type='hidden' value='%s' name='%s' />" % (token, FORM_FIELD_NAME)
        }
