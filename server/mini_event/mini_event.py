import pathlib
import base64

from .models import User, Event, UserEvent
from .app import App, Client


class MiniEventApp(App):
    """
    This class has custom logic
    """

    def __init__(self, database, settings):
        super().__init__(database, settings)
        self.events = {}

    def init_database(self):
        """
        Register the tables used by the app to ensure the database is
        initialized correctly
        """
        self.database.create_tables([User, Event, UserEvent])

    def on_server_start(self):
        """
        Called when the server starts
        """
        self.load_events()

    def load_events(self):
        """
        Load all the events from the database
        """
        for event in Event.select():
            self.events[event.id] = event

    async def on_client_connected(self, client: Client):
        """
        Called when a client connects to the server (before authentication)
        """
        self.log("Connected %s" % client.id)

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        self.log("%s is %s" % (client.id, client.user.name))
        await client.send(type="welcome", **client.to_json())

        for event in self.events.values():
            await client.send(type="event", **self.event_data(event, client.user))

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        self.log("Disconnected %s" % client.id)

    async def _on_attend(self, client: Client, data: dict):
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
        self.events.pop(event_id)

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

        data["attending"] = bool(event.attendees.filter(UserEvent.user_id==user.id).first())

        # This allows passing the attendee count so we don't have to calculate it
        # multiple times on broadcast_event_change()
        if attendees is None:
            attendees = event.attendees.count()
        data["attendees"] = attendees

        return data

    async def broadcast_event_change(self, event):
        attendees = event.attendees.count()

        for client in self.clients.values():
            await client.send(type="event", **self.event_data(event, client.user, attendees))
