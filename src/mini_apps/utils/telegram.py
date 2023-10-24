import io

from PIL import Image

import telethon

import lottie
from lottie.exporters.core import export_tgs
from lottie.exporters.cairo import export_png


def animated_sticker_file(animation):
    fileobj = io.BytesIO()
    export_tgs(animation, fileobj)
    fileobj.seek(0)
    return fileobj


def static_sticker_file(image):
    return photo_file(image, "WebP")


def photo_file(image, format, background=(0, 0, 0, 0)):
    if isinstance(image, lottie.objects.Animation):
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
        telethon.tl.types.DocumentAttributeFilename("sticker.tgs")
    ], *a, **kw)


async def send_sticker(client, chat, file):
    file.name = "sticker.webp"
    return await client.send_file(chat, file, force_document=False, attributes=[
        telethon.tl.types.DocumentAttributeFilename("sticker.webp")
    ])


class InlineHandler:
    """
    Context manager that provides a simple interface to provide inline results
    It also includes sticker support
    """
    def __init__(self, event: telethon.events.InlineQuery.Event):
        self.event = event
        self.builder = event.builder
        self.query = event.query.query
        self.results = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a, **kw):
        await self.event.answer(self.results)

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
                telethon.tl.types.DocumentAttributeFilename("sticker.webp")
            ]
        ))

    def animated_sticker(self, file):
        self.results.append(self.builder.document(
            file, "",
            mime_type="application/x-tgsticker",
            type="sticker",
            attributes=[
                telethon.tl.types.DocumentAttributeFilename("sticker.tgs")
            ]
        ))
