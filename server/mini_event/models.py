import peewee
from .db import BaseModel

class Event(BaseModel):
    title = peewee.CharField()
    description = peewee.CharField()
    image = peewee.CharField()
    duration = peewee.FloatField()
    start = peewee.CharField()

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image": self.image,
            "start": self.start,
            "duration": self.duration
        }


class User(BaseModel):
    telegram_id = peewee.IntegerField(unique=True)
    name = peewee.CharField()

    @classmethod
    def get_user(cls, telegram_data):
        user = cls.select().where(cls.telegram_id == telegram_data["id"]).first()

        name = telegram_data["first_name"]
        if telegram_data["last_name"]:
            name += " " + telegram_data["last_name"]

        if not user:
            user = cls()
            user.telegram_id = telegram_data["id"]
            user.name = name
            user.save()
        elif user.name != name:
            user.name = name
            user.save()

        return user

    def to_json(self):
        return {
            "telegram_id": self.telegram_id,
            "name": self.name
        }


class UserEvent(BaseModel):
    user = peewee.ForeignKeyField(User, backref="events")
    event = peewee.ForeignKeyField(Event, backref="users")

    class Meta:
        # `indexes` is a tuple of 2-tuples, where the 2-tuples are
        # a tuple of column names to index and a boolean indicating
        # whether the index is unique or not.
        indexes = (
            (("user", "event"), True),
        )

