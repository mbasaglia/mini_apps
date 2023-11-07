#!/usr/bin/env python3
import json
import argparse

from mini_apps.settings import Settings


parser = argparse.ArgumentParser(description="Show settings for an app")
parser.add_argument(
    "app",
    help="App name"
)
parser.add_argument(
    "--globals", "-g",
    action="store_true",
    help="Include global settings",
)


if __name__ == "__main__":
    args = parser.parse_args()
    global_settings = Settings.load_global()
    app_settings = global_settings.apps[args.app].settings

    values = {}
    if args.globals:
        value = global_settings.data
    values.update(app_settings._data)

    print(json.dumps(values, indent=4))
