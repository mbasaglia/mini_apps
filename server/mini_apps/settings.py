import importlib
import json
import logging
import pathlib
import traceback


class LogSource:
    """
    Class to simplify logging
    """
    level = logging.WARN

    def __init__(self, name):
        self.name = name
        self.log = self.get_logger(name)

    def log_exception(self, message=None, *args):
        if message:
            self.log.critical(message, *args)
        self.log.critical(traceback.format_exc())

    @classmethod
    def get_logger(cls, name):
        log = logging.getLogger(name)
        log.setLevel(cls.level)
        return log


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

    def get(self, key: str, default=None):
        """
        Get an item or the default value if not present
        """
        return getattr(self, key.replace("-", "_"), default)

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
        log = data.pop("log", {})
        super().__init__(data)

        self.init_logging(log)
        self.database = self.load_database(database)
        self.apps = SettingsValue()
        self.app_list = []
        self.database_models = []

        for name, app_settings in apps.items():
            if app_settings.pop("enabled", True):
                app = self.load_app(app_settings, name)
                setattr(self.apps, name, app)
                self.app_list.append(app)

    def log_level(self, conf_value):
        if isinstance(conf_value, int):
            return conf_value
        return getattr(logging, conf_value.upper())

    def init_logging(self, log_config):
        log = {
            "level": logging.INFO,
            "global-level": logging.WARN,
            "format": "%(asctime)s %(name)-10s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
        log.update(log_config)
        LogSource.level = self.log_level(log.pop("level"))
        log["level"] = self.log_level(log.pop("global-level"))
        logging.basicConfig(**log)

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

        LogSource.get_logger("database").info("Database %s with %s" % (db_settings.get("database"), cls.__name__))

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
            self.apps
        )
        return self.server
