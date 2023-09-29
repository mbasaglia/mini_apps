import sys
import importlib
import json
import pathlib


# TODO use python logging module
class LogSource:
    def __init__(self, name, backend):
        self.name = name
        self.backend = backend

    def log(self, message):
        self.backend.log(self.name, message)

    def log_exception(self, *message):
        self.backend.log_exception(self.name, message)


class StreamLog:
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def log(self, *message):
        self.stream.write(" ".join(map(str, message)))
        self.stream.write("\n")
        self.stream.flush()

    def log_exception(self, *message):
        self.log(*message)
        traceback.print_exc()




class SettingsValue:
    """
    Object to access settings in a more convenient way than a dict
    """
    def __init__(self, data: dict = {}):
        for key, value in data.items():
            if isinstance(value, dict):
                value = SettingsValue(value)
            setattr(self, key.replace("-", "_"), value)

    def pop(self, key: str):
        """
        Removes a setting and returns its value
        """
        value = getattr(self, key)
        delattr(self, key)
        return value

    def get(self, key):
        return getattr(self, key.replace("-", "_"), None)

    def dict(self):
        return vars(self)

    @classmethod
    def load(cls, filename, **extra):
        """
        Loads settings from a JSON file
        """
        with open(filename, "r") as settings_file:
            data = json.load(settings_file)
            data.update(extra)
            return cls(data)


class AppSettings(SettingsValue):
    """
    Access both app-specific and global settings
    """
    def __init__(self, data, global_settings):
        super().__init__(data)
        self._global = global_settings

    def __getattr__(self, name):
        if name != "_global" and hasattr(self._global, name):
            return getattr(self._global, name)

        raise AttributeError(name)


class Settings(SettingsValue):
    """
    Global settings
    """
    def __init__(self, data: dict):
        database = data.pop("database")
        apps = data.pop("apps")
        super().__init__(data)

        self.log = StreamLog()
        self.database = self.load_database(database)
        self.apps = SettingsValue()
        self.app_list = []
        self.database_models = []

        for name, app_settings in apps.items():
            if app_settings.pop("enabled", True):
                app = self.load_app(app_settings, name)
                setattr(self.apps, name, app)
                self.app_list.append(app)

    @classmethod
    def get_paths(cls):
        server_path = pathlib.Path(__file__).absolute().parent.parent
        root = server_path.parent
        settings_path = server_path / "settings.json"
        return {
            "root": root,
            "server": server_path,
            "client": root / "client",
            "settings": settings_path,
        }

    @classmethod
    def load_global(cls):
        """
        Loads the global settings file
        """
        paths = cls.get_paths()

        return cls.load(
            paths["settings"],
            paths=paths
        )

    def load_database(self, db_settings: dict):
        """
        Loads database settings
        """
        cls = self.import_class(db_settings.pop("class"))

        if cls.__name__ == "SqliteDatabase":
            database_path = self.paths.root / db_settings["database"]
            database_path.parent.mkdir(parents=True, exist_ok=True)
            db_settings["database"] = str(database_path)

        return cls(**db_settings)

    def load_app(self, app_settings: dict, name: str):
        """
        Loads a mini app / bot
        """
        cls = self.import_class(app_settings.pop("class"))
        settings = AppSettings(app_settings, self)
        app = cls(settings, name)
        app.register_models()
        return app

    def import_class(self, import_string: str):
        """
        Imports a python class from its module.class notation
        """
        module_name, class_name = import_string.rsplit(".", 1)
        return getattr(importlib.import_module(module_name), class_name)

    def connect_database(self):
        """
        Connects to the database and initializes the models
        """
        from .db import connect

        database = connect(self.database)
        database.connect()
        database.create_tables(self.database_models)
        return database

    def websocket_server(self, host=None, port=None):
        """
        Returns a WebsocketServer instance based on settings
        """
        from .websocket_server import WebsocketServer

        self.server = WebsocketServer(
            host or self.websocket.hostname,
            port or self.websocket.port,
            self.apps,
            self.log
        )
        return self.server
