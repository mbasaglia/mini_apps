import codecs
import gzip
import inspect
import io
import json

import telethon

from mini_apps.app import App, Client
from . import models
from . import document


class Glaximini(App):
    def __init__(self, *args):
        super().__init__(*args)
        self.documents = {}

    def register_models(self):
        """
        Registers the database models
        """
        self.settings.database_models += [models.User, models.Document, models.UserDoc, models.Shape, models.Keyframe]

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Start",
                    self.settings.url
                )
            ])
        ])

    async def on_telegram_start(self, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        This bot allows you to make simple animated stickers
        """), buttons=self.inline_buttons())

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        userdoc = models.UserDoc.get_or_none(models.UserDoc.user_id == client.user.id)
        if userdoc:
            doc = document.Document(userdoc.document)
        else:
            doc = document.Document.from_data({"width": 512, "height": 512, "fps": 60, "duration": 180})

        client.document = doc
        self.documents[doc.public_id] = doc
        await doc.join(client)

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        self.save_document(client)
        self.documents.pop(client.document.public_id)

    def save_document(self, client: Client):
        if client.document:
            with self.settings.database.atomic():
                client.document.save()

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        if type == "document.edit":
            if client.document:
                await client.document.edit(client, data["command"], data["data"])
        elif type == "document.save":
            self.save_document(client)
        else:
            await client.send(type="error", msg="Unknown command", what=data)

    def telegram_inline_results(self, query: telethon.events.InlineQuery):
        document_id = query.text.split(" ")[0]
        if not document_id:
            return []

        doc = self.documents.get(document_id)
        if doc:
            lottie_data = doc.cached_lottie()
        else:
            raw_id = document.decode_id(document_id)
            doc = models.Document.select(models.Document.lottie).where(models.Document.id == raw_id).first()
            if not doc:
                return []
            lottie_data = doc.lottie

        print(lottie_data)
        file = io.BytesIO()
        with gzip.open(file, "wb") as gzfile:
            lottie_data["tgs"] = 1
            json.dump(lottie_data, codecs.getwriter('utf-8')(gzfile))
        file.seek(0)

        return [query.builder.document(
            file, "",
            mime_type="application/x-tgsticker",
            type="sticker",
            attributes=[
                telethon.tl.types.DocumentAttributeFilename("sticker.tgs")
            ]
        )]

    async def on_telegram_inline(self, query: telethon.events.InlineQuery):
        """
        Called on telegram bot inline queries
        """
        await query.answer(self.telegram_inline_results(query))
