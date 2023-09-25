#!/usr/bin/env python3
import asyncio
import argparse

from mini_apps.app import Settings


async def run_server(settings):
    """
    Runs the telegram bot and socket server
    """
    tasks = []
    for app in settings.app_list:
        tasks.append(asyncio.create_task(app.run_socket_server()))
        tasks.append(asyncio.create_task(app.run_bot()))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        for task in pending:
            task.cancel()

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    settings = Settings.load_global()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Websocket bind address"
    )
    args = parser.parse_args()

    if args.host is not None:
        for app in settings.app_list:
            app.settings.hostname = args.host

    with settings.connect_database():
        asyncio.run(run_server(settings))
