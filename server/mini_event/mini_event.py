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
        self.database.create_tables([User, Event, UserEvent])

    async def handle(self, client: Client, type: str, data: dict):
        if type == "attend":
            pass  # TODO
        else:
            await client.send(type="error", msg="Unknown command", what=data)

    def load_events(self):
        for event in Event.select().where(cls.telegram_id == telegram_id):
            self.events[event.id] = event

    async def on_client_connected(self, client: Client):
        print("Connected %s" % client.id)

    async def on_client_authenticated(self, client: Client):
        #await client.send(type="welcome", **client.to_json())

        for event in self.events.values():
            await client.send(type="event", **event.to_json());

    async def on_client_disconnected(self, client: Client):
        print("Disconnected %s" % client.id)

    def get_user(self, message: dict):
        data = self.decode_telegram_data(message["data"])
        if data is None:
            return

        with self.atomic():
            user = User.get_user(data)

