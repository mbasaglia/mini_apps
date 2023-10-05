import inspect
import io
import time

import aiocron
import telethon
import PIL.Image

from mini_apps.app import App, Client



class Place(App):
    def __init__(self, *args):
        super().__init__(*args)
        self.palette = self.settings.palette
        self.width = self.settings.width
        self.height = self.settings.height
        self.start_color = self.settings.start_color
        self.delay = self.settings.delay
        self.max_color = len(self.palette)

        self.image = PIL.Image.new("P", (self.width, self.height), color=self.start_color)
        flat_palette = []
        for color in self.palette:
            flat_palette += color
        self.image.putpalette(flat_palette)

        self.png = None
        self.hash = chr(65 + self.start_color) * (self.width * self.height)
        self.broadcast_sent = False
        self.timers = {}

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Join",
                    self.settings.url
                )
            ])
        ])

    def set_pixel(self, x, y, color):
        """
        Updates the image and marks it as dirty
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.image.putpixel((x, y), color)
            self.png = None
            self.broadcast_sent = False

    def get_png(self):
        """
        Returns a (potentially upscaled) rendering of the image as a file-like object
        """
        if not self.png:
            self.png = io.BytesIO()
            if self.width < 256:
                factor = 512 // self.width
                image = self.image.resize((factor * self.width, factor * self.height), PIL.Image.Resampling.NEAREST)
            else:
                image = self.image
            image.save(self.png, "PNG")
            self.png.name = "place.png"
        self.png.seek(0)
        return self.png

    def on_server_start(self):
        """
        Called when the server starts
        """
        # Run every 5 seconds
        aiocron.crontab('* * * * * */5', func=self.broadcast_changes)

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        min_time = self.timers.get(client.user.telegram_id, 0)
        curr_time = time.time()
        await client.send("delay", delay=max(0, curr_time - min_time))
        await client.send("setup", width=self.width, height=self.height, palette=self.palette)
        await client.send("refresh", hash=self.hash)

    @App.bot_command("start", description="Start message")
    async def on_telegram_start(self, args: str, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(
            event.chat,
            "Collaboarative project where telegram users can draw a pixel every %s minutes" % self.delay,
            file=self.get_png(),
            buttons=self.inline_buttons()
        )

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        if type == "pixel":
            curr_time = time.time()
            min_time = self.timers.get(client.user.telegram_id, 0)
            if curr_time < min_time:
                await client.send("delay", delay=curr_time - min_time)
                return

            delay_seconds = 60 * self.delay

            try:
                x = int(data["x"])
                y = int(data["y"])
                color = int(data["color"])
                self.set_pixel(x, y, color)
            except Exception:
                # Throttle sussy people
                delay_seconds *= 60
                self.log_exception()

            if not client.user.is_admin:
                self.timers[client.user.telegram_id] = curr_time + delay_seconds
            await client.send("delay", delay=delay_seconds)

    async def broadcast_changes(self):
        """
        Sends the updated image at most every 5 seconds
        """
        if self.broadcast_sent:
            return

        self.broadcast_sent = True
        self.hash = ""
        for y in range(self.height):
            for x in range(self.width):
                self.hash += chr(65 + self.image.getpixel((x, y)))

        for client in self.clients.values():
            await client.send(type="refresh", hash=self.hash)

