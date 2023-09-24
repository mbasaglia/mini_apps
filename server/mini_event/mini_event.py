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
        await client.send(type="welcome", **client.to_json())

        for event in self.events.values():
            await client.send(type="event", **self.event_data(event, client.user))

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        self.log("Disconnected %s" % client.id)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        self.log(client.id, data)

        if type == "attend":
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

        elif type == "leave":
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

        else:
            await client.send(type="error", msg="Unknown command", what=data)

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
