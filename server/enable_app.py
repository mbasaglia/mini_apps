#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys

from mini_apps.settings import Settings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enables a mini app")
    parser.add_argument(
        "python_class",
        type=str,
        help="Fully qualified python class"
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="App name in settings"
    )
    parser.add_argument(
        "--write-settings",
        "-w",
        action="store_true",
        help="Write the settings file"
    )
    args = parser.parse_args()

    paths = Settings.get_paths()
    module_name, class_name = args.python_class.rsplit(".", 1)

    print("Installing files")
    source_path = paths["server"] / pathlib.Path(module_name.replace(".", "/")).parent
    dest_path = paths["client"]
    for source_file in source_path.iterdir():
        if source_file.suffix != ".py" and source_file.name != "__pycache__":
            dest_file = dest_path / source_file.name
            if not dest_file.exists():
                dest_file.symlink_to(source_file)

    # Figure out the settings for the app
    with open(paths["settings"], "r") as settings_file:
        settings_data = json.load(settings_file)

    app_id = args.name or source_path.name

    if app_id in settings_data["apps"]:
        app_data = settings_data["apps"][app_id]
        if app_data["class"] != args.python_class:
            sys.stderr.write("Python class mismatch\n")
            sys.exit(1)
        else:
            print("Enabling in settings")
            is_enabled = app_data.pop("enabled", True)
            # Don't edit settings
            if is_enabled:
                print("Already configured")
                sys.exit(0)
    else:
        # Find an already defined app for defaults
        best_app = None
        for app in settings_data["apps"].values():
            is_enabled = app.get("enabled", True)
            if not best_app:
                best_app = app

            if is_enabled:
                best_app = app
                break

        # No app defined, use dummy values
        if not best_app:
            best_app = {
                "bot-token": "(your bot token)",
                "api-id": "(your api id)",
                "api-hash": "(your api hash)",
                "url": "https://(your domain)/foo.html",
                "media-url": "https://(your domain)/media/"
            }

        settings_data["apps"][app_id] = {
            "class": args.python_class,
            "bot-token": "(your bot token)",
            "api-id": best_app["api-id"],
            "api-hash": best_app["api-hash"],
            "url": "%s/%s.html" % (best_app["url"].rsplit("/", 1)[0], source_path.name),
            "media-url": best_app["media-url"]
        }

    # Output the settings JSON
    if args.write_settings:
        print("Updating settings")
        with open(paths["settings"], "w") as settings_file:
            json.dump(settings_data, settings_file, indent=4)
    else:
        print(json.dumps(settings_data["apps"][app_id], indent=4))
