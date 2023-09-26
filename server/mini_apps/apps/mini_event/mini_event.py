import base64
import datetime
import inspect
import mimetypes
import pathlib
import time

import aiocron
import telethon

from mini_apps.models import User
from mini_apps.app import App, Client
from .models import Event, UserEvent


class MiniEventApp(App):
    """
    This class has custom logic
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.events = {}
        self.sorted_events = []

    def register_models(self):
        """
        Registers the database models
        """
        self.settings.databse_models += [User, Event, UserEvent]

    def on_server_start(self):
        """
        Called when the server starts
        """
        self.load_events()

        # Run every minute
        aiocron.crontab('* * * * * 0', func=self.check_starting)

    def load_events(self):
        """
        Load all the events from the database
        """
        for event in Event.select():
            self.events[event.id] = event

        self.sorted_events = sorted(self.events.values())

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        self.log("%s is %s" % (client.id, client.user.name))

        for event in self.sorted_events:
            await client.send(type="event", **self.event_data(event, client.user))

        await client.send(
            type="events-loaded",
            selected=client.user.telegram_data.get("start_param", None)
        )

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        self.log("Disconnected %s" % client.id)

    async def _on_attend(self, client: Client, data: dict):
        """
        Called on an `attend` message
        """
        # Get the event
        event_id = data.get("event", "")
        event = self.events.get(event_id)
        if not event:
            await client.send(type="error", msg="No such event")
            return

        # Create the relation if it doesn't exist
        created = UserEvent.get_or_create(user_id=client.user.id, event_id=event_id)[1]

        # Update the event on all clients
        if created:
            await self.broadcast_event_change(event)

    async def _on_leave(self, client: Client, data: dict):
        """
        Called on an `leave` message
        """
        # Get the event
        event_id = data.get("event", "")
        event = self.events.get(event_id)
        if not event:
            await client.send(type="error", msg="No such event")
            return

        # If the user is attending the event, delete the attendance
        attendance = UserEvent.get_or_none(user_id=client.user.id, event_id=event_id)
        if attendance:
            attendance.delete_instance()
            await self.broadcast_event_change(event)

    async def _on_create_event(self, client: Client, data: dict):
        """
        Called on an `create-event` message
        """
        # Check if the user is an admin
        if not client.user.is_admin:
            await client.send(type="error", msg="You are not an admin")
            return

        try:
            event = Event()
            event.title = data["title"]
            event.description = data["description"]
            event.duration = float(data["duration"])
            event.start = data["start"]
            image_name = data["image"]["name"].replace("/", "_")
            root = pathlib.Path(__file__).absolute().parent.parent.parent
            image_path = root / "client" / "media" / image_name

            # Save the image, avoiding overwriting existing ones
            image_path = self.unique_filename(image_path)
            with open(image_path, "wb") as image_file:
                image_file.write(base64.b64decode(data["image"]["base64"]))

            event.image = "media/" + image_path.name

            event.save()

            await self.broadcast_event_change(event)

        except Exception as exception:
            self.log(exception)
            await client.send(type="error", msg="Invalid data")

    async def _on_delete_event(self, client: Client, data: dict):
        """
        Called on an `delete-event` message
        """
        # Check if the user is an admin
        if not client.user.is_admin:
            await client.send(type="error", msg="You are not an admin")
            return

        # Get the event object
        event_id = data.get("id")
        event = Event.get_or_none(id=event_id)

        # Nothing to do if it doesn't exist
        if not event:
            return

        # Delete from the dabase
        event.delete_instance(recursive=True)
        ev = self.events.pop(event_id)
        try:
            self.sorted_events.pop(self.sorted_events.index(ev))
        except ValueError:
            pass

        # Broadcast the change to all users
        for client in self.clients.values():
            await client.send(type="delete-event", id=event_id)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        self.log(client.id, data)

        # User attends an event
        if type == "attend":
            await self._on_attend(client, data)
        # User no longer attends an event
        elif type == "leave":
            await self._on_leave(client, data)
        # Admin creates an event
        elif type == "create-event":
            await self._on_create_event(client, data)
        # Admin creates an event
        elif type == "delete-event":
            await self._on_delete_event(client, data)
        # Unknown message type
        else:
            await client.send(type="error", msg="Unknown command", what=data)

    def unique_filename(self, path: pathlib.Path):
        """
        Returns a file name that does not exist based on an input filename
        """
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        attempt_index = 1
        while path.exists():
            name = "%s_%s%s" % (stem, attempt_index, suffix)
            path = parent / name
            attempt_index += 1

        return path

    def event_data(self, event: Event, user: User, attendees: int = None):
        """
        Formats an event, adding user-specific data
        """
        data = event.to_json()

        data["attending"] = bool(event.attendees.filter(UserEvent.user_id == user.id).first())

        # This allows passing the attendee count so we don't have to calculate it
        # multiple times on broadcast_event_change()
        if attendees is None:
            attendees = event.attendees.count()
        data["attendees"] = attendees

        return data

    async def broadcast_event_change(self, event):
        """
        Sends an event to all connected clients
        """
        attendees = event.attendees.count()

        for client in self.clients.values():
            await client.send(type="event", **self.event_data(event, client.user, attendees))

    async def on_telegram_start(self, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """

        # Send a short message and a button to open the app on telegram
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        This bot allows you to sign up for events
        """), buttons=self.inline_buttons())

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "View Events",
                    self.settings.url
                )
            ])
        ])

    async def on_telegram_inline(self, query: telethon.events.InlineQuery):
        """
        Called on telegram bot inline queries
        """
        events = []
        # Telegram supports up to 50 inline results
        limit = 50

        # Specific event from the web app
        if query.text.startswith("event:"):
            try:
                event_id = int(query.text.split(":")[1])
                event = Event.get_or_none(id=event_id)
                if event:
                    events = [event]
            except Exception:
                return
        # Not enough to search, show all
        elif len(query.text) < 2:
            events = self.sorted_events[:limit]
        # Text-based search
        else:
            pattern = query.text.lower()

            for i in range(min(limit, len(self.sorted_events))):
                event = self.sorted_events[i]
                if pattern in event.title.lower() or pattern in event.description.lower():
                    events.append(event)

        # Format and return the results
        results = []

        for event in events:
            image_url = self.settings.media_url + event.image

            text = inspect.cleandoc("""
            **{event.title}**[\u200B]({image_url})
            {event.description}

            **Starts at** {event.start}
            **Duration** {event.duration:g} hours

            [View Events]({url}?startapp={event.id})
            """).format(
                event=event,
                url="https://t.me/%s/events" % self.telegram_me.username,
                image_url=image_url
            )

            preview_text = inspect.cleandoc("""
            {event.description}
            Starts at {event.start}. Duration: {event.duration:g} hours
            """).format(
                event=event
            )

            results.append(query.builder.article(
                title=event.title,
                description=preview_text,
                text=text,
                #buttons=self.inline_buttons(),
                thumb=telethon.tl.types.InputWebDocument(
                    image_url,
                    size=0,
                    mime_type=mimetypes.guess_type(event.image)[0],
                    attributes=[]
                ),
                link_preview=True,
            ))

        await query.answer(results)

    async def check_starting(self):
        """
        Called periodically, used to check if the user needs to be notified of
        an event
        """
        now = datetime.datetime.now()
        hour = now.strftime("%H:%M")
        message_count = 0
        for event in self.sorted_events:
            if event.start > hour:
                break
            elif event.start == hour:
                text = "**{event.title}** is starting!".format(event=event)
                for user in event.attendees:
                    try:
                        # We can't send more than 30 messages (to diferent chats)
                        # per second, so we wait if that happens
                        message_count += 1
                        if message_count >= 30:
                            message_count = 0
                            time.sleep(1)

                        await self.telegram.send_message(
                            user.user.telegram_id,
                            message=text
                        )

                    except Exception as exception:
                        self.log("Notification error %s %s" % (exception.__clas__, exception))
                        pass
