import json
import inspect
import datetime
import mimetypes

import aiohttp
import asyncio
from yarl import URL
from markupsafe import Markup

from mini_apps.telegram.bot import TelegramMiniApp
from mini_apps.telegram.command import admin_command, bot_command
from mini_apps.service import BaseService, ServiceStatus
from mini_apps.http.web_app import template_view, format_minutes
from mini_apps.telegram.events import InlineQueryEvent, NewMessageEvent
from mini_apps.telegram import tl
from mini_apps.markdown.html_to_markdown import html_to_markdown


class PollingService(BaseService):
    def __init__(self, settings, callback, delay_seconds):
        super().__init__(settings)
        self.callback = callback
        self.delay_seconds = delay_seconds
        self.sleep_task = None

    async def run(self):
        self.status = ServiceStatus.Starting

        try:
            self.keep_running = True
            loop = asyncio.get_running_loop()
            self.poll_future = loop.create_future()
            self.status = ServiceStatus.Running
            while self.keep_running:
                task = asyncio.shield(self.poll_future)
                await self.callback()
                try:
                    await asyncio.wait_for(task, self.delay_seconds)
                except TimeoutError:
                    pass
            self.status = ServiceStatus.Disconnected
        except Exception:
            self.status = ServiceStatus.Crashed
            self.log_exception()

    async def stop(self):
        self.keep_running = False
        if self.poll_future and not self.poll_future.cancelled():
            self.poll_future.cancel()


class JsonPath:
    def __init__(self, path: str):
        self.chunks = path.split("/") if path else []

    def get(self, obj):
        for chunk in self.chunks:
            if isinstance(obj, list):
                obj = obj[int(chunk)]
            else:
                obj = obj[chunk]

        return obj


def markdown(text):
    import re
    import markdown
    from mini_apps.markdown.autolink import AutoLinkExtension

    return Markup(markdown.markdown(
        # force blocks for ul lists
        re.sub(r"(\n(?:\s*[-*] [^\n]*\n)+)", r"\n\1", text),
        extensions=[AutoLinkExtension()],
    ))


class JsonStructure:
    class Object:
        def __init__(self, data):
            self.data = data

        def get(self, path: str):
            return JsonPath(str).get(self.data)

        def __json__(self):
            data = dict(vars(self))
            data.pop("data")
            return data

    class Field:
        def __init__(self, structure, key: str, url: URL):
            self.key = key
            if url.scheme == "eval":
                expr = url.path

                def conv(obj):
                    return eval(expr, globals(), {"self": obj})

                self.conversion = conv
                self.path = None
            else:
                self.conversion = structure.conversions.get(url.scheme)
                self.path = JsonPath(url.path)

        def apply(self, obj):
            if self.path is None:
                val = self.conversion(obj)
            else:
                val = self.path.get(obj.data)
                if self.conversion:
                    val = self.conversion(val)
            setattr(obj, self.key, val)

    def __init__(self, data, datetime_format):
        self.datetime_format = datetime_format
        self.conversions = {
            "datetime": self.datetime,
            "date": datetime.date.fromisoformat,
            "null": lambda x: None,
            "markdown": markdown,
            "html": Markup,
            "str": str,
        }

        self.fields = []
        for k, v in data.items():
            self.fields.append(self.Field(self, k, URL(v)))

    def datetime(self, val):
        if not self.datetime_format:
            return datetime.datetime.fromisoformat(val)
        return datetime.datetime.strptime(val, self.datetime_format)

    def object(self, data):
        obj = self.Object(data)
        for field in self.fields:
            field.apply(obj)
        return obj


class ApiEventApp(TelegramMiniApp):
    def __init__(self, settings):
        super().__init__(settings)
        self.api_url = self.settings["api-url"]
        poll_frequency = int(self.settings.get("poll", 20)) * 60
        self.poller = PollingService(settings, self.load_commands, poll_frequency)
        self.data = None
        self.events = {}
        self.sorted_events = []
        self.days = []
        self.path_events = JsonPath(self.settings["path-events"])
        self.event_structure = JsonStructure(
            self.settings["event-data"],
            self.settings.get("datetime-format", None)
        )

    async def run(self):
        await asyncio.gather(
            self.poller.run(),
            super().run()
        )

    async def stop(self):
        await asyncio.gather(
            self.poller.stop(),
            super().stop()
        )

    async def load_commands(self):
        async with aiohttp.client.ClientSession() as session:
            response = await session.get(self.api_url, headers={"User-Agent": "MiniApps %s" % self.name})

            try:
                self.data = json.loads(await response.read())
            except Exception:
                self.data = {}

            self.events = {}
            for evdata in self.path_events.get(self.data):
                evobj = self.event_structure.object(evdata)
                self.events[evobj.id] = evobj

            self.sorted_events = sorted(self.events.values(), key=lambda e: e.start)

            self.days = []
            day = None
            for event in self.sorted_events:
                if event.day != day:
                    day = event.day
                    self.days.append({"day": day, "events": []})
                self.days[-1]["events"].append(event)

    @template_view("/", template="events.html")
    async def index(self, request):
        now = datetime.datetime.now(datetime.timezone.utc)

        curr_id = request.url.query.get("tgWebAppStartParam", "")
        curr_event = None
        curr_day = "ongoing"

        if curr_id is not None:
            curr_event = self.events.get(curr_id, None)
        else:
            for event in self.sorted_events:
                if event.finish > now:
                    curr_event = event
                    curr_id = event.id
                    break

        if curr_event:
            curr_day = curr_event.day.isoformat()

        return {
            "data": self.data,
            "events": self.events,
            "days": self.days,
            "now": now,
            "current": self.current_events(now),
            "active_day": curr_day,
            "active_event": curr_id
        }

    def current_events(self, now, upcoming=0):
        current_events = []
        for event in self.sorted_events:
            if event.start <= now <= event.finish:
                current_events.append(event)
            elif event.start > now:
                if upcoming > 0:
                    current_events.append(event)
                    upcoming -= 1
                else:
                    break
        return current_events

    def current_and_future(self, now):
        current_events = []
        for event in self.sorted_events:
            if now <= event.finish:
                current_events.append(event)
        return current_events

    def events_from_query(self, query: str, now):
        # Telegram supports up to 50 inline results
        limit = 50

        # Specific event from the web app
        if query.startswith("event:"):
            event_id = query.split(":")[1]
            event = self.events.get(event_id)
            if event:
                return [event]
            else:
                return []

        # Not enough to search, show all
        if len(query) < 2:
            return self.current_and_future(now)[:limit]

        # Text-based search
        pattern = query.lower()
        events = []
        for event in self.sorted_events:
            if pattern in event.title.lower() or pattern in (event.description or "").lower():
                events.append(event)
                if len(events) >= limit:
                    break
        return events

    def thumb(self, event):
        if not event.image:
            return None

        return tl.types.InputWebDocument(
            event.image,
            size=0,
            mime_type=mimetypes.guess_type(event.image)[0],
            attributes=[]
        )

    def file_preview(self, url):
        return tl.types.InputMediaWebPage(
            url,
            force_large_media=True,
            optional=True,
        )

    async def on_telegram_inline(self, query: InlineQueryEvent):
        """
        Called on telegram bot inline queries
        """
        results = []
        template = self.get_template("event.md")
        now = datetime.datetime.now(datetime.timezone.utc)
        mini_app_link = self.mini_app_link()

        for event in self.events_from_query(query.text, now):
            text = await self.render_template(template, dict(
                event=event,
                html_to_markdown=html_to_markdown,
                mini_app_link=mini_app_link,
                now=now
            ))
            if event.image:
                text = "[\u200B](%s)%s" % (event.image, text)

            preview_text = inspect.cleandoc("""
            {start}, {duration}
            {description}
            """).format(
                start=event.start.strftime("%A %d %H:%M"),
                description=html_to_markdown(event.description or ""),
                duration=format_minutes(event.duration)
            )

            results.append(query.builder.article(
                title=event.title,
                description=preview_text,
                text=text,
                #buttons=self.inline_buttons(),
                thumb=self.thumb(event),
                link_preview=True,
            ))

        await query.answer(results)

    def mini_app_link(self):
        return "https://t.me/{username}/{shortname}".format(
            username=self.telegram_me.username,
            shortname=self.settings["short-name"],
        )

    @bot_command
    async def schedule(self, args: str, msgev: NewMessageEvent):
        """
        Shows a link to open the schedule app
        """
        mini_app_link = self.mini_app_link()
        await self.telegram.send_message(
            msgev.chat,
            "[View Events](%s)" % mini_app_link,
            link_preview=True,
        )

    @bot_command
    async def events(self, args: str, msgev: NewMessageEvent):
        """
        Shows current and upcoming events
        """
        mini_app_link = self.mini_app_link()

        if not isinstance(msgev.chat, tl.types.User):
            await self.telegram.send_message(
                msgev.chat,
                "[View Events](%s)" % mini_app_link,
                link_preview=True,
                reply_to=msgev.message,
                file=self.file_preview(mini_app_link)
            )
            return

        template = self.get_template("event.md")
        now = datetime.datetime.now(datetime.timezone.utc)

        events = self.current_events(now, 3)
        if not events:
            await self.telegram.send_message(
                msgev.chat,
                "No upcoming events\n\n[View Events](%s)" % mini_app_link,
                # link_preview=True,
                file=self.file_preview(mini_app_link)
            )

        for event in events:
            text = await self.render_template(template, dict(
                event=event,
                html_to_markdown=html_to_markdown,
                mini_app_link=mini_app_link,
                now=now
            ))

            await self.telegram.send_message(
                msgev.chat,
                text,
                link_preview=True,
                thumb=self.thumb(event)
            )

    @admin_command
    async def refresh_events(self, args: str, msgev: NewMessageEvent):
        """
        Reloads the events from the API
        """
        await self.load_commands()
