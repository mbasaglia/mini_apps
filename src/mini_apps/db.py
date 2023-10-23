import json
import peewee

from .service import BaseService, Service, ServiceProvider, ServiceStatus


class JSONField(peewee.TextField):
    """
    Field that stores data as JSON
    """
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


class BaseModel(peewee.Model):
    """
    Model helper to set the database at runtime
    """
    class Meta:
        database = peewee.DatabaseProxy()


def connect(database):
    """
    Updates BaseModel and returns the database connection
    """
    BaseModel._meta.database.initialize(database)
    return database


class Database(BaseService):
    """
    Database connection service
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.provider = ServiceProvider("database", self)
        self.database_models = []
        db_settings = dict(settings.dict())
        cls = self.settings.import_class(db_settings.pop("db_class"))
        db_settings.pop("_global")

        if cls.__name__ == "SqliteDatabase" and db_settings["database"] != ":memory:":
            database_path = settings.paths.root / db_settings["database"]
            database_path.parent.mkdir(parents=True, exist_ok=True)
            db_settings["database"] = str(database_path)

        self.log.debug("Database %s with %s" % (db_settings.get("database"), cls.__name__))

        self.database = cls(**db_settings)

    def register_consumer(self, what: str, service: "Service"):
        self.provider.register_app(service)

    def provides(self):
        return [self.provider.name]

    async def run(self):
        self.status = ServiceStatus.Starting
        try:
            connect(self.database)
            self.database.connect()
            self.database.create_tables(self.database_models)
            self.status = ServiceStatus.Running
            self.provider.on_start()

        except Exception:
            self.status = ServiceStatus.Crashed
            self.log_exception()

    async def stop(self):
        self.provider.on_stop()
        self.database.close()
        self.status = ServiceStatus.Disconnected


class ServiceWithModels(Service):
    def on_provider_added(self, provider: ServiceProvider):
        super().on_provider_added(provider)
        if provider.name == "database":
            self.database = provider.service.database
            provider.service.database_models += self.database_models()

    def database_models(self):
        """
        Override in derived classes to register the models
        """
        return []

    def consumes(self):
        return super().consumes() + ["database"]
