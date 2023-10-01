#!/usr/bin/env python3
import argparse

from mini_apps.settings import Settings
from mini_apps.models import User


parser = argparse.ArgumentParser(description="Shows a list of users, with their telegram ID, admin status and name")

if __name__ == "__main__":
    args = parser.parse_args()

    settings = Settings.load_global()

    with settings.connect_database():
        print("    Telegram ID | Admin | Name")
        for user in User.select():
            print("%15s | %5s | %s" % (user.telegram_id, user.is_admin, user.name))
