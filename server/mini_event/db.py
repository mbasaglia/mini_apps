import peewee


class BaseModel(peewee.Model):
    class Meta:
        database = peewee.DatabaseProxy()


def connect(database):
    BaseModel._meta.database.initialize(database)
    return database
