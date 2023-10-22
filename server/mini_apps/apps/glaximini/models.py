
import peewee

from mini_apps.db import BaseModel, JSONField


class Document(BaseModel):
    url = peewee.CharField(default="")
    width = peewee.IntegerField(default=512)
    height = peewee.IntegerField(default=512)
    fps = peewee.IntegerField(default=60)
    duration = peewee.IntegerField(default=180)
    start = peewee.IntegerField(default=0)
    lottie = JSONField(default={})


class UserDoc(BaseModel):
    telegram_id = peewee.IntegerField()
    document = peewee.ForeignKeyField(Document, backref="users")

    class Meta:
        # `indexes` is a tuple of 2-tuples, where the 2-tuples are
        # a tuple of column names to index and a boolean indicating
        # whether the index is unique or not.
        indexes = (
            (("telegram_id", "document"), True),
        )


class Shape(BaseModel):
    public_id = peewee.CharField()
    document = peewee.ForeignKeyField(Document, backref="shapes")
    shape = peewee.CharField()
    props = JSONField()
    parent_id = peewee.CharField(null=True)

    class Meta:
        # `indexes` is a tuple of 2-tuples, where the 2-tuples are
        # a tuple of column names to index and a boolean indicating
        # whether the index is unique or not.
        indexes = (
            (("public_id", "document"), True),
        )


class Keyframe(BaseModel):
    time = peewee.FloatField()
    props = JSONField()
    shape = peewee.ForeignKeyField(Shape, backref="keyframes")
