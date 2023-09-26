import peewee
from mini_apps.db import BaseModel
from mini_apps.models import User


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

    def __lt__(self, other):
        return (self.start, self.id) < (other.start, other.id)


class UserEvent(BaseModel):
    user = peewee.ForeignKeyField(User, backref="events")
    event = peewee.ForeignKeyField(Event, backref="attendees")

    class Meta:
        # `indexes` is a tuple of 2-tuples, where the 2-tuples are
        # a tuple of column names to index and a boolean indicating
        # whether the index is unique or not.
        indexes = (
            (("user", "event"), True),
        )
