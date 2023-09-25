#!/usr/bin/env python3
import argparse
import pathlib
import shutil

from mini_apps.app import Settings
from mini_apps.models import User


parser = argparse.ArgumentParser(description="Lists registered users")
args = parser.parse_args()

settings = Settings.load_global()

with settings.connect_database():
    print("    Telegram ID | Admin | Name")
    for user in User.select():
        print("%15s | %5s | %s" % (user.telegram_id, user.is_admin, user.name))
