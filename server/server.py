#!/usr/bin/env python3
import argparse
import asyncio
import subprocess
import sys

from mini_apps.settings import Settings
from mini_apps.server import Server


async def run_server(settings, host, port, reload):
    """
    Runs the telegram bot and socket server
    """

    server = Server(settings)
    reload = await server.run(host, port, reload)
    if reload:
        try:
            p = subprocess.run(sys.argv)
            sys.exit(p.returncode)
        except KeyboardInterrupt:
            return


settings = Settings.load_global(__name__ != "__main__")

parser = argparse.ArgumentParser(description="Runs the server")
parser.add_argument(
    "--host",
    type=str,
    default=None,
    help="Websocket bind address"
)
parser.add_argument(
    "--port", "-p", "-P",
    type=str,
    default=None,
    help="Websocket port"
)
parser.add_argument(
    "--reload", "-r",
    action="store_true",
    help="If present, auto-reloads the server when sources change"
)
parser.add_argument(
    "--no-reload", "-nr",
    action="store_true",
    help="If present disables auto-reloading"
)


if __name__ == "__main__":
    args = parser.parse_args()

    reload = not args.no_reload and (args.reload or settings.get("reload"))
    try:
        asyncio.run(run_server(settings, args.host, args.port, reload))
    except KeyboardInterrupt:
        pass
