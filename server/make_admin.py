#!/usr/bin/env python3
import argparse
import pathlib
import shutil

from mini_event.mini_event import MiniEventApp
from mini_event.models import User


parser = argparse.ArgumentParser(description="Make a user an admin")
parser.add_argument("telegram_id", type=int)
args = parser.parse_args()

app = MiniEventApp.from_settings()


with app.connect():
    app.init_database()

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
