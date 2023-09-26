#!/usr/bin/env python3
import argparse

from mini_apps.settings import Settings
from mini_apps.models import User


parser = argparse.ArgumentParser(description="Make a user an admin")
parser.add_argument("telegram_id", type=int)
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
