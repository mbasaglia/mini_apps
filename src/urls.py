#!/usr/bin/env python3
import argparse

from mini_apps.server import Server
from mini_apps.settings import Settings
from mini_apps.http.route_info import RouteInfo

parser = argparse.ArgumentParser(description="Lists HTTP server URLs")


def print_resources(resources):
    for res in resources:
        print(res)
        if res.children:
            print_resources(res.children)


if __name__ == "__main__":
    args = parser.parse_args()
    settings = Settings.load_global()
    server = Server(settings)
    server.load_services(None, None)

    print_resources(RouteInfo.from_app(server.providers["http"].app))
