import os
import json
import logging
import pathlib
import importlib
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
        self.log_formatted_exception(traceback.format_exc())

    def log_formatted_exception(self, message):
        self.log.critical(message)

    @classmethod
    def get_logger(cls, name):
        log = logging.getLogger(name)
        log.setLevel(cls.level)
        return log


def dict_merge_recursive(orig: dict, overrides: dict):
    for key, val in overrides.items():
        if key not in orig or not isinstance(val, dict):
            orig[key] = val
        else:
            dict_merge_recursive(orig[key], val)

class VarsLoader:
    prefix = "$vars."
    this_prefix = "$this."

    def __init__(self, data):
        self.vars = data.pop("$vars")
        self.apply(data)

    def apply(self, data: dict):
        for key, val in data.items():
            if isinstance(val, dict):
                self.apply(val)
            elif isinstance(val, str):
                if val.startswith(self.prefix):
                    varname = val[len(self.prefix):]
                    if varname.startswith("$"):
                        varname = data[varname[1:]]
                    data[key] = self.vars[varname]
                elif val.startswith(self.this_prefix):
                    varname = val[len(self.this_prefix):]
                    data[key] = data[varname[1:]]
            elif isinstance(val, list):
                for sub in val:
                    if isinstance(sub, dict):
                        self.apply(sub)


class SettingsValue:
    """
    Object to access settings in a more convenient way than a dict
    """
    def __init__(self, data: dict = {}):
        for key, value in data.items():
            if isinstance(value, dict):
                value = SettingsValue(value)
            setattr(self, key.replace("-", "_"), value)

    def __contains__(self, item):
        return item in self.dict()

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
            if "$include" in data:
                include_path = filename.parent / data.pop("$include")
                with open(include_path, "r") as include:
                    dict_merge_recursive(data, json.load(include))
            if "$vars" in data:
                VarsLoader(data)
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

    def __contains__(self, item):
        return item in self.dict() or item in self._global


class Settings(SettingsValue):
    """
    Global settings
    """
    def __init__(self, data: dict):
        apps = data.pop("apps")
        log = data.pop("log", {})
        super().__init__(data)

        self.init_logging(log)
        self.apps = SettingsValue()
        self.app_list = []

        for app_settings in apps:
            if app_settings.pop("enabled", True):
                app = self.load_app(app_settings)
                self.add_app(app)

    def add_app(self, app):
        if app.name in self.apps:
            raise KeyError("Duplicate app %s" % app.name)
        setattr(self.apps, app.name, app)
        self.app_list.append(app)
        return app

    def ensure_app(self, cls, name_hint=None):
        if not name_hint:
            name_hint = cls.default_name()

        existing = self.apps.get(name_hint)
        if isinstance(existing, cls):
            return existing

        existing = None

        for app in self.app_list:
            if isinstance(app, cls):
                return app

        return self.add_app(name_hint, cls(name_hint, AppSettings({}, self)))

    @property
    def database(self):
        if not self._database and self._database_settings:
            self._database = self.load_database(self._database_settings)
        return self._database

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
        settings_path = root / "settings.json"
        env_path = os.environ.get("SETTINGS", "")
        if env_path:
            settings_path = pathlib.Path(env_path)
        elif not settings_path.exists():
            curdir_settings = pathlib.Path() / "settings.json"
            if curdir_settings.exists():
                settings_path = curdir_settings

        return {
            "root": root,
            "server": server_path,
            "settings": settings_path,
        }

    @classmethod
    def load_global(cls):
        """
        Loads the global settings file

        :param fallback: If True, it will load a minimal default configuration without raising errors
        """
        paths = cls.get_paths()
        return cls.load(
            paths["settings"],
            paths=paths
        )

    def load_app(self, app_settings: dict):
        """
        Loads a mini app / bot
        """
        cls = self.import_class(app_settings.pop("class"))
        settings = AppSettings(app_settings, self)
        app = cls(settings)
        return app

    def import_class(self, import_string: str):
        """
        Imports a python class from its module.class notation
        """
        module_name, class_name = import_string.rsplit(".", 1)
        return getattr(importlib.import_module(module_name), class_name)
