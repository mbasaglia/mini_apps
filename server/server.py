#!/usr/bin/env python3
import asyncio
import argparse

from mini_apps.settings import Settings


async def run_server(settings, host, port):
    """
    Runs the telegram bot and socket server
    """

    database = settings.connect_database()
    tasks = []

    websocket_server = settings.websocket_server(host, port)
    tasks.append(asyncio.create_task(websocket_server.run()))

    for app in settings.app_list:
        tasks.append(asyncio.create_task(app.run_bot()))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        for task in pending:
            task.cancel()

    except KeyboardInterrupt:
        pass

    finally:
        print("Shutting down")
        database.close()


if __name__ == "__main__":
    settings = Settings.load_global()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        type=str,
        default=settings.websocket.hostname,
        help="Websocket bind address"
    )
    parser.add_argument(
        "--port", "-p", "-P",
        type=str,
        default=settings.websocket.port,
        help="Websocket port"
    )
    args = parser.parse_args()

    asyncio.run(run_server(settings, args.host, args.port))
