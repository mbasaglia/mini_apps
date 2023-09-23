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
        for event in Event.select().where(cls.telegram_id == telegram_id):
            self.events[event.id] = event

    async def on_client_connected(self, client: Client):
        """
        Called when a client connects to the server (before authentication)
        """
        print("Connected %s" % client.id)
        await client.send(type="connect")

    def get_user(self, message: dict):
        """
        Authenticates the user based on the mini app initData
        """
        data = self.decode_telegram_data(message["data"])
        if data is None:
            return

        with self.atomic():
            user = User.get_user(data)

        return user

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        await client.send(type="welcome", **client.to_json())

        for event in self.events.values():
            await client.send(type="event", **event.to_json());

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        print("Disconnected %s" % client.id)

    async def handle(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        print(client.id, message)

        if type == "attend":
            pass  # TODO
        else:
            await client.send(type="error", msg="Unknown command", what=data)
