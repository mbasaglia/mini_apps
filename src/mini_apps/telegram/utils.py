import io
import asyncio

from PIL import Image

from telethon.helpers import add_surrogate

from . import tl
from .events import InlineQueryEvent, NewMessageEvent


def animated_sticker_file(animation):
    from lottie.exporters.core import export_tgs
    fileobj = io.BytesIO()
    export_tgs(animation, fileobj)
    fileobj.seek(0)
    return fileobj


def static_sticker_file(image):
    return photo_file(image, "WebP")


def photo_file(image, format, background=(0, 0, 0, 0)):
    import lottie
    if isinstance(image, lottie.objects.Animation):
        from lottie.exporters.cairo import export_png
        data_png = io.BytesIO()
        export_png(image, data_png)
        data_png.seek(0)
        image = Image.open(data_png)

    out_image = io.BytesIO()
    image.save(
        out_image,
        format=format,
        background=background,
    )
    out_image.seek(0)
    out_image.name = "file." + format.lower()
    return out_image


async def send_animated_sticker(client, chat, file, *a, **kw):
    return await client.send_file(chat, file, attributes=[
        tl.types.DocumentAttributeFilename("sticker.tgs")
    ], *a, **kw)


async def send_sticker(client, chat, file):
    file.name = "sticker.webp"
    return await client.send_file(chat, file, force_document=False, attributes=[
        tl.types.DocumentAttributeFilename("sticker.webp")
    ])


class InlineHandler:
    """
    Context manager that provides a simple interface to provide inline results
    It also includes sticker support
    """
    def __init__(self, event: InlineQueryEvent):
        self.event = event
        self.builder = event.builder
        self.query = event.query.query
        self.results = []
        #For how long this result should be cached on the user's client. Defaults to 0 for no cache.
        self.cache_time = 0
        # Whether the results should show as a gallery (grid) or not.
        self.gallery = False
        self.switch_webview = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a, **kw):
        await self.answer()

    async def answer(self):
        if self.results:
            results = await asyncio.gather(*self.results)
        else:
            results = []
        await self.event.client(
            tl.functions.messages.SetInlineBotResultsRequest(
                query_id=self.event.query.query_id,
                results=results,
                cache_time=self.cache_time,
                gallery=self.gallery,
                next_offset=None,
                private=False,
                switch_pm=None,
                switch_webview=self.switch_webview
            )
        )

    def document(self, *a, **kw):
        self.results.append(self.builder.document(*a, **kw))

    def game(self, *a, **kw):
        self.results.append(self.builder.game(*a, **kw))

    def photo(self, *a, **kw):
        self.results.append(self.builder.photo(*a, **kw))

    def sticker(self, file):
        file.name = "sticker.webp"
        self.results.append(self.builder.document(
            file, "",
            mime_type="image/webp",
            type="sticker",
            attributes=[
                tl.types.DocumentAttributeFilename("sticker.webp")
            ]
        ))

    def animated_sticker(self, file):
        self.results.append(self.builder.document(
            file, "",
            mime_type="application/x-tgsticker",
            type="sticker",
            attributes=[
                tl.types.DocumentAttributeFilename("sticker.tgs")
            ]
        ))

    def webview_button(self, text: str, url: str):
        self.switch_webview = tl.types.InlineBotWebView(text, url)


class MessageMarkup:
    def to_data(self):
        raise NotImplementedError


class InlineKeyboard(MessageMarkup):
    def __init__(self):
        self.rows = []

    def add_row(self):
        self.rows.append([])

    def add_button(self, button, row):
        if not self.rows:
            self.add_row()

        self.rows[row].append(button)

    def add_button_url(self, *args, row=-1, **kwargs):
        self.add_button(tl.types.KeyboardButtonUrl(*args, **kwargs), row)

    def add_button_callback(self, text, data, row=-1):
        self.add_button(tl.types.KeyboardButtonCallback(text, data), row)

    def add_button_webview(self, *args, row=-1, **kwargs):
        self.add_button(tl.types.KeyboardButtonWebView(*args, **kwargs), row)

    def to_data(self):
        return self.rows


class MessageFormatter:
    class EntityTag:
        def __init__(self, entity_type, formatter, **kwargs):
            self.type = getattr(tl.types, "MessageEntity" + entity_type)
            self.formatter = formatter
            self.offset = 0
            self.kwargs = kwargs

        def open(self):
            self.offset = self.formatter.offset

        def close(self):
            self.formatter.entities.append(self.type(
                offset=self.offset,
                length=self.formatter.offset - self.offset
            ))

        def __enter__(self):
            self.open()
            return self

        def __exit__(self, ex_type, exc, trace):
            self.close()

    def __init__(self):
        self.text = ""
        self.entities = []
        self.offset = 0

    def __iadd__(self, text):
        self.text += text
        self.offset += self.text_length(text)
        return self

    def _add_entity(self, type, text, **kwargs):
        length = self.text_length(text)
        self.entities.append(type(
            offset=self.offset,
            length=length,
            **kwargs
        ))
        self.text += text
        self.offset += length

    def bold(self, text):
        self._add_entity(tl.types.MessageEntityBold, text)

    def italic(self, text):
        self._add_entity(tl.types.MessageEntityItalic, text)

    def strike(self, text):
        self._add_entity(tl.types.MessageEntityStrike, text)

    def underline(self, text):
        self._add_entity(tl.types.MessageEntityUnderline, text)

    def code(self, text):
        self._add_entity(tl.types.MessageEntityCode, text)

    def pre(self, text, language=""):
        self._add_entity(tl.types.MessageEntityPre, text, language=language)

    def mention(self, text, user_id):
        self._add_entity(tl.types.InputMessageEntityMentionName, text, user_id=user_id)

    def block_quote(self):
        return self.EntityTag("Blockquote", self)

    def bot_command(self, text):
        self._add_entity(MessageFormatter.tl.types.MessageEntityBotCommand, text)

    @staticmethod
    def text_length(text):
        return len(add_surrogate(text))


class MessageChunk:
    def __init__(self, client, text, entity):
        self.client = client
        self.text = text
        self.entity = entity
        self.is_mention_name = isinstance(self.entity, tl.types.MessageEntityMentionName)
        self.is_mention_username = isinstance(self.entity, tl.types.MessageEntityMention)
        self.is_mention = self.is_mention_name or self.is_mention_username
        self.is_text = entity is None

    async def load(self):
        if isinstance(self.entity, tl.types.MessageEntityMentionName):
            self.is_mention = True
            self.mentioned_user = await self.client.get_input_entity(self.entity.user_id)
            self.mentioned_id = self.entity.user_id
            self.mentioned_name = self.text
        elif isinstance(self.entity, tl.types.MessageEntityMention):
            try:
                self.mentioned_user = await self.client.get_entity(self.text)
                self.mentioned_id = self.mentioned_user.id
                self.mentioned_name = user_name(self.mentioned_user)
            except Exception:
                self.mentioned_user = None
                self.mentioned_id = None
                self.mentioned_name = self.text

    def __repr__(self):
        return "<MessageChunk %r%s>" % (
            self.text,
            " " + self.entity.__class__.__name__ if self.entity else ""
        )


async def parse_text(event: NewMessageEvent):
    """
    Returns a list of MessageChunk
    """
    if not event.entities:
        return [MessageChunk(event.client, event.message.message, None)]
    chunks = []
    start_index = 0
    for entity in event.entities:
        if start_index < entity.offset:
            chunks.append(MessageChunk(event.client, event.message.message[start_index:entity.offset], None))
        end_index = entity.offset + entity.length
        text = event.message.message[entity.offset:end_index]
        start_index = end_index
        chunks.append(MessageChunk(event.client, text, entity))

    if start_index < len(event.message.message):
        chunks.append(MessageChunk(event.client, event.message.message[start_index:], None))

    for chunk in chunks:
        chunk.message = event
    return chunks


async def mentions_from_message(event: NewMessageEvent):
    """
    Returns a dict of id => name from mentions in event
    """
    ids = {}
    for entity in await parse_text(event):
        if entity.is_mention:
            await entity.load()
            ids[str(entity.mentioned_id)] = entity.mentioned_name

    if len(ids) == 0 and event.message.is_reply:
        message = await event.message.get_reply_message()
        sender = await message.get_sender()
        ids = {str(sender.id): user_name(sender)}
    return ids


def user_name(user):
    name = user.first_name or ""
    if user.last_name:
        name += " " + user.last_name

    name = name.strip()
    if name:
        return name

    if user.username:
        return user.username

    return "Unnamed user"


async def set_admin_title(client, chat, user, title):
    user = await client.get_input_entity(user)
    entity = await client.get_input_entity(chat)
    rights = tl.types.ChatAdminRights(other=True)
    return await client(tl.functions.channels.EditAdminRequest(entity, user, rights, rank=title))
