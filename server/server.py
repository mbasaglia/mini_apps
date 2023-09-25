#!/usr/bin/env python3
import asyncio
import argparse

from mini_event.mini_event import MiniEventApp


if __name__ == "__main__":
    app = MiniEventApp.from_settings()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", "-p", "-P",
        type=int,
        default=app.settings["port"],
        help="Websocket port number"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=app.settings["hostname"],
        help="Websocket bind address"
    )
    args = parser.parse_args()

    app.settings["port"] = args.port
    app.settings["hostname"] = args.host

    asyncio.run(app.run())
