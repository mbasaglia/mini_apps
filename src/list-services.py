#!/usr/bin/env python3
import sys
import argparse

from mini_apps.settings import Settings


def format_value(value):
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (list, tuple, set)):
        return ",".join(map(format_value, value))
    return str(value)


def format_field(service, field_name, field_func):
    if not field_func:
        value = getattr(service, field_name)
        if callable(value):
            value = value()
    else:
        value = field_func(service)

    return format_value(value)


def format_service(service, fields):
    return [format_field(service, name, value) for name, value in fields]


def format_services(services, fields, show_titles):
    rows = [format_service(service, fields) for service in services]
    if show_titles:
        rows.insert(0, [f[0] for f in fields])
    lengths = [
        max(len(rows[s][i]) for s in range(len(services)))
        for i in range(len(fields))
    ]

    for row in rows:
        for length, field in zip(lengths, row):
            sys.stdout.write(field.ljust(length))
            sys.stdout.write(" ")
        sys.stdout.write("\n")


fields = {
    "name": None,
    "class": lambda service: "%s.%s" % (service.__class__.__module__, service.__class__.__name__),
    "runnable": None,
    "autostart": None,
    "provides": None,
    "consumes": None,
}

parser = argparse.ArgumentParser(description="List configured services")
parser.add_argument(
    "--all", "-a",
    action="store_true",
    help="Show all services (including non-runnable ones)"
)
parser.add_argument(
    "--show-title", "-t",
    action="store_true",
)
parser.add_argument(
    "--fields", "-f",
    nargs="+",
    default=["name", "autostart"],
    choices=list(fields.keys()),
    help="Fields to show"
)
parser.add_argument(
    "--long", "-l",
    action="store_const",
    const=list(fields.keys()),
    dest="fields",
    help="Show all fields"
)

if __name__ == "__main__":
    args = parser.parse_args()

    settings = Settings.load_global()
    services = [app for app in settings.app_list if args.all or app.runnable]
    filtered_fields = [f for f in fields.items() if f[0] in args.fields]
    format_services(services, filtered_fields, args.show_title)
