import time
import datetime

import peewee
import aiocron

from mini_apps.db import BaseModel, ServiceWithModels
from mini_apps.service import Client
from .api_events import ApiEventApp


class FavedEvent(BaseModel):
    event_id = peewee.CharField()
    telegram_id = peewee.CharField()
    notified = peewee.DateTimeField(null=True, default=None)

    def key(self):
        return (self.event_id, self.telegram_id)


class DbStoreApiEventApp(ApiEventApp, ServiceWithModels):
    def __init__(self, settings):
        super().__init__(settings)
        self.notification_minutes = datetime.timedelta(minutes=settings.get("notify-before", 15))
        self.user_faved = {}
        self.supports_faving = True

    def database_models(self):
        """
        Registers the database models
        """
        return [FavedEvent]

    async def check_starting(self):
        """
        Called periodically, used to check if the user needs to be notified of
        an event
        """
        now = datetime.datetime.now()
        resend = now - datetime.timedelta(hours=1)
        notify_before = now + self.notification_minutes
        message_count = 0
        for event in self.sorted_events:
            if event.start > now:
                break
            elif event.start <= notify_before:
                text = "**{event.title}** is starting!".format(event=event)
                faved = FavedEvent.select().where(FavedEvent.notified.is_null() | FavedEvent.notified < resend)
                for user in faved:
                    try:
                        # We can't send more than 30 messages (to diferent chats)
                        # per second, so we wait if that happens
                        message_count += 1
                        if message_count >= 30:
                            message_count = 0
                            time.sleep(1)

                        await self.telegram.send_message(
                            user.telegram_id,
                            message=text
                        )
                        user.notified = now
                        user.save()

                    except Exception:
                        self.log_exception("Notification error")
                        pass

    def on_provider_start(self, provider):
        """
        Called when the server starts
        """
        super().on_provider_start(provider)

        if provider.name == "database":
            self.load_faved()

            # Run every minute
            aiocron.crontab('* * * * * 0', func=self.check_starting)

    def load_faved(self):
        """
        Load all the events from the database
        """
        self.user_faved = {}
        self.event_faved = {}

        for event in FavedEvent.select():
            try:
                self.user_faved[event.telegram_id][event.id] = event
            except KeyError:
                self.user_faved[event.telegram_id] = {event.id: event}

    async def _on_attend(self, client: Client, data: dict):
        event = self._event_from_message(client, data)
        if event:
            FavedEvent.get_or_create(telegram_id=client.user.telegram_id, event_id=event.id)[1]
            self.user_faved.setdefault(client.user.telegram_id, {})[event.id] = event
            self.confirm_event_change(client, event, True)

    async def _on_leave(self, client: Client, data: dict):
        event = self._event_from_message(client, data)
        if event:
            attendance = FavedEvent.get_or_none(telegram_id=client.user.telegram_id, event_id=event.id)
            if attendance:
                attendance.delete_instance()
            self.user_faved.setdefault(client.user.telegram_id, {}).pop(event.id, None)
            self.confirm_event_change(client, event, False)

    async def confirm_event_change(self, client: Client, event, attends):
        await client.send(type="event", **self.event_data(event, attends))

    def event_data(self, event, attends):
        return {
            "id": event.id,
            "attending": attends
        }
