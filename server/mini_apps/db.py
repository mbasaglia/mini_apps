import json
import peewee


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
