import codecs
import gzip
import inspect
import io
import json
import random
import uuid

import telethon

from mini_apps.app import App, Client


class Glaximini(App):

    def __init__(self, *args):
        super().__init__(*args)
        self.lotties = {}

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
        # Send the initial count when the client connects
        client.lottie_id = str(uuid.uuid4())
        self.lotties[client.lottie_id] = client

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        #self.lotties.pop(client.lottie_id)
        pass

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        if type == "sticker":
            self.lotties[client.lottie_id] = data["lottie"]
            # Only used to avoid telegram cache
            random_stuff = "%06d" % random.randint(0, 999999)
            await client.send(type="sticker-id", id="%s %s" % (client.lottie_id, random_stuff))
        else:
            await client.send(type="error", msg="Unknown command", what=data)

    def telegram_inline_results(self, query: telethon.events.InlineQuery):
        client_id = query.text.split(" ")[0]
        if not client_id:
            return []

        lottie_data = self.lotties.get(client_id);
        if not lottie_data:
            return []

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
