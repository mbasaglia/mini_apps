import hmac
import time
import hashlib
import datetime
import dataclasses


def clean_telegram_auth(data: dict, bot_token: str, max_age=datetime.timedelta(days=1), key_prefix: bytes = None):
    clean = dict(data)
    hash = clean.pop("hash", None)
    if not hash:
        return None

    data_check = sorted(
        "%s=%s" % (key, value)
        for key, value in clean.items()
    )
    data_check_string = "\n".join(data_check)

    # Check the hash
    token = bot_token.encode("ascii")
    if key_prefix:
        secret_key = hmac.new(key_prefix, token, digestmod=hashlib.sha256).digest()
    else:
        secret_key = hashlib.sha256(token).digest()
    correct_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    # If the hash is invalid, return None
    if hash != correct_hash:
        return None

    # Check age
    now = datetime.datetime.now()
    max_age_seconds = max_age.total_seconds()
    if max_age_seconds > 0 and time.mktime(now.timetuple()) - float(clean["auth_date"]) > max_age_seconds:
        return None

    return clean


@dataclasses.dataclass
class User:
    telegram_id: int
    name: str
    telegram_username: str = ""
    is_admin: bool = False
    pfp: str = None

    @classmethod
    def from_telegram_user(cls, user):
        return cls.from_telegram_dict(vars(user))

    @classmethod
    def from_telegram_dict(cls, telegram_data):
        name = telegram_data["first_name"]
        last_name = telegram_data.get("last_name")
        if last_name:
            name += " " + last_name

        return cls(
            name=name,
            telegram_id=telegram_data["id"],
            pfp=telegram_data.get("photo_url", None),
            telegram_username=telegram_data.get("username", ""),
        )

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

    def filter_telegram_id(self, telegram_id, name: str = ""):
        """
        Filters a user from a telegram message
        """
        return self.filter_user(User(telegram_id=telegram_id, name=name))

    @staticmethod
    def from_settings(settings):
        if "banned" in settings or "admins" in settings:
            return SettingsListUserFilter(
                set(settings.get("banned", [])),
                set(settings.get("admins", [])),
                settings.get("admin_only", False),
            )
        return UserFilter()


class SettingsListUserFilter(UserFilter):
    """
    Ban/admin list filter
    """
    def __init__(self, banned, admins, admin_only):
        self.banned = banned
        self.admins = admins
        self.admin_only = admin_only

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
        elif self.admin_only:
            return None

        return user
