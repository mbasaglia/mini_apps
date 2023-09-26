import peewee
from .db import BaseModel

class User(BaseModel):
    telegram_id = peewee.IntegerField(unique=True)
    name = peewee.CharField()
    is_admin = peewee.BooleanField(default=False)

    @classmethod
    def get_user(cls, telegram_data):
        user = cls.get_or_none(cls.telegram_id == telegram_data["id"])

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
            "name": self.name,
            "is_admin": self.is_admin,
        }
