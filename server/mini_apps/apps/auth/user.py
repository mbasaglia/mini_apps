import dataclasses


@dataclasses.dataclass
class User:
    telegram_id: int
    name: str
    is_admin: bool = False

    @classmethod
    def from_telegram_dict(cls, telegram_data):
        name = telegram_data["first_name"]
        last_name = telegram_data.get("last_name")
        if last_name:
            name += " " + last_name

        return cls(name=name, telegram_id=telegram_data["id"])

    @classmethod
    def from_json(cls, json_dict):
        return cls(**json_dict)

    def to_json(self):
        return {
            "telegram_id": self.telegram_id,
            "name": self.name,
            "is_admin": self.is_admin,
        }


class UserFilter:
    """
    Class that filters logged in users for websocket and telegram input
    """
    def filter_user(self, user):
        """
        Filter users

        Override in derived classes
        """
        return user

    def filter_telegram_id(self, telegram_id):
        """
        Filters a user from a telegram message
        """
        return self.filter_user(User(telegram_id=telegram_id))

    @staticmethod
    def from_settings(settings):
        if "banned" in settings or "admins" in settings:
            return SettingsListUserFilter(set(settings.get("banned", [])), set(settings.get("admins", [])))
        return UserFilter()


class SettingsListUserFilter(UserFilter):
    """
    Ban/admin list filter
    """
    def __init__(self, banned, admins):
        self.banned = banned
        self.admins = admins

    def filter_user(self, user):
        """
        Filter users

        Users in the ban list will not be connected, users in the admin list will be marked as admins
        """
        if not user:
            return None

        if user.telegram_id in self.banned:
            return None

        if user.telegram_id in self.admins:
            user.is_admin = True

        return user
