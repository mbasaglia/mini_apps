#!/usr/bin/env python3
import argparse
import pathlib
import shutil

from mini_apps.settings import Settings
from mini_apps.apps.mini_event.mini_event import Event


parser = argparse.ArgumentParser(description="Adds an event to the database")
parser.add_argument(
    "--title", "-t",
    help="Event title",
    required=True
)
parser.add_argument(
    "--description", "-d",
    help="Event description",
    required=True
)
parser.add_argument(
    "--image", "-i",
    type=pathlib.Path,
    required=True,
    help="""
    Image path.
    It will be copied over to the media directory.
    Note that images should be less than 512 KB in size, have a 16:9 aspect ratio and should be at least 400 pixels wide.
    """
)
parser.add_argument(
    "--start", "-s",
    help="Start time, in HH:MM format",
    required=True
)
parser.add_argument(
    "--duration", "-r",
    help="Number of hours the event lasts for",
    type=float,
    required=True
)


if __name__ == "__main__":
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
