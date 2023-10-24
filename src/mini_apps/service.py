import enum
import json
import inspect
import pathlib

from .settings import LogSource, Settings
from .apps.auth.user import User


class Client:
    """
    Client object, contains a socket for the connection and a user for data
    """
    def __init__(self, socket):
        self.id = id(self)
        self.socket = socket
        self.user: User = None
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
    def __init__(self, settings: Settings):
        super().__init__(settings.get("name", self.default_name()))
        self.settings = settings
        self.status = ServiceStatus.Disconnected
        self.server = None
        self.autostart = settings.get("autostart", True)

    @property
    def runnable(self):
        """
        Whether the service has a meanining ful run()
        """
        return True

    @property
    def is_running(self):
        return self.status.value >= ServiceStatus.Starting.value or not self.runnable

    async def run(self):
        """
        Should run the service until disconnected
        """
        raise NotImplementedError()

    async def stop(self):
        """
        Stops run() from running
        """
        pass

    @classmethod
    def default_name(cls):
        """
        Returns the default name for this service
        """
        chunks = cls.__module__.split(".")
        if chunks[-1] == "app":
            return chunks[-2]
        return chunks[-1]

    def register_consumer(self, what: str, service: "Service"):
        raise NotImplementedError

    def provides(self):
        """
        List of manager service names provided by this service
        """
        return []

    def consumes(self):
        """
        List of manager service names this service uses
        """
        return []


class MetaService(type):
    def __new__(cls, name, bases, attrs):
        meta_processors = attrs.get("meta_processors", set())
        for base in bases:
            meta_processors |= getattr(base, "meta_processors", set())

        for meta_processor in meta_processors:
            meta_processor(name, bases, attrs)

        created = super().__new__(cls, name, bases, attrs)
        created.meta_processors = meta_processors
        return created


class Service(BaseService, metaclass=MetaService):
    """
    Service that can be registered on HttpServer
    """

    def on_provider_added(self, provider: "ServiceProvider"):
        """
        Called when the app is added to the service provider
        """
        pass

    def on_provider_start(self, provider: "ServiceProvider"):
        """
        Called when the service provider starts
        """
        pass

    def on_provider_stop(self, provider: "ServiceProvider"):
        """
        Called when the service provider stops
        """
        pass

    @classmethod
    def get_server_path(cls):
        """
        Returns the path for containing the module that defines class
        """
        return pathlib.Path(inspect.getfile(cls)).absolute().parent

    def add_routes(self, http):
        """
        Registers routes to the web server
        """
        raise NotImplementedError


class LogRetainingService(BaseService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception_log = ""

    def log_formatted_exception(self, message):
        super().log_formatted_exception(message)
        self.exception_log += "\n" + message
        self.exception_log = self.exception_log[-1024:]


class ServiceProvider:
    def __init__(self, name, service: BaseService):
        self.name = name
        self.apps = {}
        self.service = service

    def register_app(self, app: Service):
        self.apps[app.name] = app
        app.on_provider_added(self)

    def on_start(self):
        for app in self.apps.values():
            app.on_provider_start(self)

    def on_stop(self):
        for app in self.apps.values():
            app.on_provider_stop(self)
