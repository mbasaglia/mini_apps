#!/usr/bin/env python3
import argparse
import pathlib
import shutil

from mini_apps.settings import Settings
from mini_apps.apps.mini_event import Event


parser = argparse.ArgumentParser(description="Adds an event to the database")
parser.add_argument("--title", "-t", required=True)
parser.add_argument("--description", "-d", required=True)
parser.add_argument("--image", "-i", type=pathlib.Path, required=True)
parser.add_argument("--start", "-s", required=True)
parser.add_argument("--duration", "-r", type=float, required=True)

args = parser.parse_args()

settings = Settings.load_global()

image_source = args.image.resolve()
image_dest = settings.paths.client / "media" / image_source.name

if image_source != image_dest:
    print("Copying image")
    shutil.copy(image_source, image_dest)

with settings.connect_database():
    event = Event()
    event.title = args.title
    event.description = args.description
    event.start = args.start
    event.duration = args.duration
    event.image = image_source.name
    event.save()
