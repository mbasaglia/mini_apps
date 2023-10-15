import enum
import json
import inspect
import pathlib

from .settings import LogSource
from .models import User


class Client:
    """
    Client object, contains a socket for the connection and a user for data
    """
    def __init__(self, socket):
        self.id = id(self)
        self.socket = socket
        self.user = None
        self.app = None

    async def send(self, **data):
        await self.socket.send_str(json.dumps(data))

    def to_json(self):
        return self.user.to_json()


class ServiceStatus(enum.Enum):
    """
    Enumeration that describe the status of a service
    """
    Disconnected = enum.auto()
    Crashed = enum.auto()
    Starting = enum.auto()
    StartFlood = enum.auto()
    Running = enum.auto()


class BaseService(LogSource):
    """
    Abstract class for services that can run on the server
    """
    def __init__(self, settings, name):
        super().__init__(name or self.__class__.__name__)
        self.settings = settings
        self.status = ServiceStatus.Disconnected
        self.server = None
        if not self.settings.get("url"):
            self.settings.url = "%s/%s/" % (self.settings.server.url.rstrip("/"), self.name)

    async def run(self):
        """
        Should run the service until disconnected
        """
        print(self)
        breakpoint()
        raise NotImplementedError()


class Service(BaseService):
    """
    Service that can be registered on HttpServer
    """

    def add_routes(self, http):
        """
        Registers routes to the web server
        """
        pass

    def register_models(self):
        """
        Override in derived classes to register the models in self.settings.database_models
        """
        pass

    def on_server_start(self):
        """
        Called when the server starts
        """
        pass

    @classmethod
    def get_server_path(cls):
        """
        Returns the path for containing the module that defines class
        """
        return pathlib.Path(inspect.getfile(cls)).absolute().parent


class UserFilter:
    """
    Class that filters logged in users for websocket and telegram input
    """
    def filter_user(self, user):
        """
        Filter users

        Override in derived classes
        """
        return user

    def filter_telegram_id(self, telegram_id):
        """
        Filters a user from a telegram message
        """
        return self.filter_user(User(telegram_id=telegram_id))

    @staticmethod
    def from_settings(settings):
        if "banned" in settings or "admins" in settings:
            return SettingsListUserFilter(set(settings.get("banned", [])), set(settings.get("admins", [])))
        return UserFilter()


class SettingsListUserFilter(UserFilter):
    """
    Ban/admin list filter
    """
    def __init__(self, banned, admins):
        self.banned = banned
        self.admins = admins

    def filter_user(self, user):
        """
        Filter users

        Users in the ban list will not be connected, users in the admin list will be marked as admins
        """
        if not user:
            return None

        if user.telegram_id in self.banned:
            return None

        if user.telegram_id in self.admins:
            user.is_admin = True

        return user


class SocketService(Service):
    """
    Service that can handle socket connections
    """
    def __init__(self, settings, name):
        super().__init__(settings, name)
        self.clients = {}
        self.filter = UserFilter.from_settings(settings)

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        pass

    async def login(self, client: Client, message: dict):
        """Login logic

        :param client: Client requesting to log in
        :param message: Data as sent from the client
        """
        client.user = self.filter.filter_user(self.get_user(message))
        if client.user:
            self.clients[client.id] = client

    def get_user(self, message: dict):
        """
        Called to authenticate a user based on the mini app initData
        Return None if authentication fails, otherwise return a user object
        """
        return None

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Override to handle socket messages
        """
        pass

    async def disconnect(self, client: Client):
        """
        Disconnects the given client
        """
        self.clients.pop(client.id)
        self.log.debug("#%s Disconnected", client.id)
        await self.on_client_disconnected(client)

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        pass
