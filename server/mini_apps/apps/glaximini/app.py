import codecs
import gzip
import inspect
import io
import json

import telethon

from mini_apps.bot import Bot
from mini_apps.service import Client
from . import models
from . import document


class Glaximini(Bot):
    def __init__(self, *args):
        super().__init__(*args)
        self.documents = {}
        self.help_pic = None

    def database_models(self):
        """
        Registers the database models
        """
        return [models.Document, models.UserDoc, models.Shape, models.Keyframe]

    def add_routes(self, http):
        """
        Registers routes to the web server
        """
        http.add_static_web_app(self, self.get_server_path() / "client")

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Open Editor",
                    self.settings.url
                )
            ])
        ])

    @Bot.bot_command("start", description="Shows the start message")
    async def on_telegram_start(self, args: str, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        This bot allows you to make simple animated stickers.
        If you need help with the user interface, use /help
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
            with self.database.atomic():
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

        try:
            raw_id = document.decode_id(document_id)
        except Exception:
            document_id = None
            raw_id = None

        if not document_id:
            ud = (
                models.UserDoc.select(models.UserDoc.document_id)
                .join(models.User)
                .where(models.User.telegram_id == query.query.user_id)
            ).first()
            if not ud:
                return []
            document_id = document.encode_id(ud.document_id)
            raw_id = ud.document_id

        doc = self.documents.get(document_id)
        if doc:
            lottie_data = doc.cached_lottie()
        else:
            doc = models.Document.select(models.Document.lottie).where(models.Document.id == raw_id).first()
            if not doc:
                return []
            lottie_data = doc.lottie

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

    @Bot.bot_command
    async def help(self, text: str, event: telethon.events.NewMessage):
        """
        Shows a description of the Mini App user interface
        """
        if self.help_pic is None:
            with open(self.settings.paths.root / "docs" / "apps" / "glaximini-ui.png", "rb") as f:
                self.help_pic = io.BytesIO(f.read())
                self.help_pic.name = "glaximini.png"

        self.help_pic.seek(0)

        await self.telegram.send_message(
            event.chat,
            inspect.cleandoc("""
            **Select**: This tool allows you to move and edit the shapes, just click on a shape to select it, drag a shape to move it,
            or drag on the handles of the selected shape to edit its properties.

            **Rectangle** and **Ellipse**: These tools are very similar, you drag on the canvas to create the corresponding shape.

            **Bezier**: This tools can create more complex shapes. Just click on the canvas to add vertices,
            if you click on the starting point the shape will be closed. You can also click and drag to make the edges more curved.

            **Undo**, **Redo**: Self explanatory.

            **Send Sticker**: Selects a chat and sends the current animation as sticker there.

            **Delete**: Delete the selected shape.

            **Fill** and **Stroke** color: They show a color selector and that will change the style of the current shape.

            **Canvas**: Here is where you see and edit the animation.

            **Play** and **Pause**: They start and stop playback.

            **Add Keyframe**: Adds a keyframe at the current frame for all the properties of the selected shape.
            """),
            file=self.help_pic
        )
