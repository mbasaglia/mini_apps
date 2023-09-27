import inspect
import json

import telethon

from mini_apps.app import App, Client


class Glaximini(App):

    def __init__(self, *args):
        super().__init__(*args)
        # Click count, this resets when the server restarts
        self.click_count = 0

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
        client.lottie = "";
        await client.send(type="clicks-updated", count=self.click_count)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        if type == "document.start":
            client.lottie = ""
        elif type == "document.chunk":
            client.lottie += data["data"]
        elif type == "document.end":
            client.lottie = json.loads(client.lottie)
        else:
            await client.send(type="error", msg="Unknown command", what=data)
