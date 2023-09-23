import peewee


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
