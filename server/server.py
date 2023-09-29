#!/usr/bin/env python3
import argparse
import asyncio
import logging
import traceback
import subprocess
import sys

from mini_apps.settings import Settings
from mini_apps.reloader import Reloader


async def coro_wrapper(coro):
    """
    Awaits a coroutine and prints exceptions (if any)
    """
    try:
        await coro
    except KeyboardInterrupt:
        pass
    except asyncio.exceptions.CancelledError:
        pass
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise


async def run_server(settings, host, port, reload):
    """
    Runs the telegram bot and socket server
    """

    database = settings.connect_database()
    tasks = []
    reloader = Reloader(settings.paths.server)

    websocket_server = settings.websocket_server(host, port)
    tasks.append(asyncio.create_task(coro_wrapper(websocket_server.run()), name="websocket"))

    for app in settings.app_list:
        tasks.append(asyncio.create_task(coro_wrapper(app.run_bot()), name=app.name))
        tasks += app.server_tasks()

    logger = logging.getLogger("server")

    reload = False
    try:
        reload = await reloader.watch()

    except KeyboardInterrupt:
        pass

    finally:
        logger.info("Shutting down")
        database.close()
        websocket_server.stop()

        for task in tasks:
            logger.debug("Stopping", task.get_name())
            task.cancel()

        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        logger.debug("All stopped")

        if reload:
            logging.info("\nReloading\n")
            p = subprocess.run(sys.argv)
            sys.exit(p.returncode)


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
    parser.add_argument(
        "--reload", "-r",
        action="store_true",
        help="If present, auto-reloads the server when sources change"
    )
    args = parser.parse_args()

    asyncio.run(run_server(settings, args.host, args.port, args.reload or settings.get("reload")))
