#!/usr/bin/env python3
import argparse

from mini_apps.settings import Settings
from mini_apps.models import User


parser = argparse.ArgumentParser(description="""Makes a user an admin.

If the user doesn't exist in the database, it will be created.
You can use `server/list_users.py` to find the right telegram ID.
""")
parser.add_argument("telegram_id", type=int)

if __name__ == "__main__":
    args = parser.parse_args()

    settings = Settings.load_global()

    with settings.connect_database():
        user, created = User.get_or_create(
            telegram_id=args.telegram_id,
            defaults={
                "name": "admin",
                "is_admin": True
            }
        )
        if not created and not user.is_admin:
            user.is_admin = True
            user.save()
