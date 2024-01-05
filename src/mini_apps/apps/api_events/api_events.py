import json
import datetime

import aiohttp
import asyncio
from yarl import URL
from markupsafe import Markup

from mini_apps.telegram.bot import TelegramMiniApp
from mini_apps.service import BaseService, ServiceStatus
from mini_apps.http.web_app import template_view


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
    import markdown
    return Markup(markdown.markdown(text))


class JsonStructure:
    class Object:
        def __init__(self, data):
            self.data = data

        def get(self, path: str):
            return JsonPath(str).get(self.data)

    class Field:
        conversions = {
            "datetime": datetime.datetime.fromisoformat,
            "date": datetime.date.fromisoformat,
            "null": lambda x: None,
            "markdown": markdown,
            "html": Markup,
        }

        def __init__(self, key: str, url: URL):
            self.key = key
            if url.scheme == "eval":
                expr = url.path

                def conv(obj):
                    return eval(expr, globals(), {"self": obj})

                self.conversion = conv
                self.path = None
            else:
                self.conversion = self.conversions.get(url.scheme)
                self.path = JsonPath(url.path)

        def apply(self, obj):
            if self.path is None:
                val = self.conversion(obj)
            else:
                val = self.path.get(obj.data)
                if self.conversion:
                    val = self.conversion(val)
            setattr(obj, self.key, val)

    def __init__(self, data):
        self.fields = []
        for k, v in data.items():
            self.fields.append(self.Field(k, URL(v)))

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
        self.poller = PollingService(settings, self.poll, poll_frequency)
        self.data = None
        self.events = []
        self.days = []
        self.path_events = JsonPath(self.settings["path-events"])
        self.event_structure = JsonStructure(self.settings["event-data"])

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

    async def poll(self):
        async with aiohttp.client.ClientSession() as session:
            response = await session.get(self.api_url, headers={"User-Agent": "MiniApps %s" % self.name})
            self.data = json.loads(await response.read())
            events = [
                self.event_structure.object(event)
                for event in self.path_events.get(self.data)
            ]

            self.events = sorted(events, key=lambda e: e.start)

            self.days = []
            day = None
            for event in self.events:
                if event.day != day:
                    day = event.day
                    self.days.append({"day": day, "events": []})
                self.days[-1]["events"].append(event)

    @template_view("/", template="events.html")
    async def index(self, request):
        return {
            "data": self.data,
            "events": self.events,
            "days": self.days,
        }
