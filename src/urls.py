#!/usr/bin/env python3
import inspect
import argparse

from aiohttp.web_urldispatcher import PrefixedSubAppResource, PlainResource, StaticResource, DynamicResource

from mini_apps.server import Server
from mini_apps.settings import Settings
from mini_apps.http.utils import FileResource, NakedSubAppResource

parser = argparse.ArgumentParser(description="Lists HTTP server URLs")


def print_resource(path, name, dest):
    print("%s%s -> %s" % (
        path,
        " (%s)" % name if name else "",
        dest
    ))


def format_handler(handler):
    if inspect.isfunction(handler) or inspect.ismethod(handler):
        return "%s.%s" % (handler.__module__, handler.__qualname__)
    return str(handler)


def print_app(app):
    for resource in app.router.resources():
        info = resource.get_info()
        if isinstance(resource, FileResource):
            print_resource(info["prefix"], resource.name, info["file"])
        elif isinstance(resource, PlainResource):
            print_resource(info["path"], resource.name, format_handler(resource._routes[0].handler))
        elif isinstance(resource, PrefixedSubAppResource):
            print_resource(info["prefix"], resource.name, "app")
            print_app(info["app"])
        elif isinstance(resource, StaticResource):
            print_resource(info["prefix"], resource.name, info["directory"])
        elif isinstance(resource, DynamicResource):
            print_resource(info["formatter"], resource.name, format_handler(resource._routes[0].handler))
        elif isinstance(resource, NakedSubAppResource):
            print_resource(".", resource.name, "app")
            print_app(info["app"])
        else:
            print(resource, info)


if __name__ == "__main__":
    args = parser.parse_args()
    settings = Settings.load_global()
    server = Server(settings)
    server.load_services(None, None)

    print_app(server.providers["http"].app)
