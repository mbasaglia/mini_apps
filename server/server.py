#!/usr/bin/env python3
import argparse
import asyncio
import traceback
import subprocess
import sys

from mini_apps.settings import Settings, LogSource
from mini_apps.reloader import Reloader


async def coro_wrapper(coro, logger: LogSource):
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
        logger.log_exception()
        raise


def create_task(method, *args):
    coro = method(*args)
    wrapped = coro_wrapper(coro, method.__self__)
    return asyncio.create_task(wrapped, name=method.__self__.name)


async def run_server(settings, host, port, reload):
    """
    Runs the telegram bot and socket server
    """

    database = settings.connect_database()
    tasks = []

    websocket_server = settings.websocket_server(host, port)
    tasks.append(create_task(websocket_server.run))

    for app in settings.app_list:
        tasks.append(create_task(app.run_bot))
        tasks += app.server_tasks()

    logger = LogSource.get_logger("server")

    try:
        if not reload:
            await asyncio.Future()
        else:
            server_path = settings.paths.server
            paths = [
                server_path / "mini_apps",
                server_path / "server.py",
                server_path / "settings.json"
            ]
            reloader = Reloader(paths)
            reload = await reloader.watch()

    except KeyboardInterrupt:
        pass

    finally:
        logger.info("Shutting down")
        database.close()
        websocket_server.stop()

        for task in tasks:
            logger.debug("Stopping %s", task.get_name())
            task.cancel()

        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        logger.debug("All stopped")

        if reload:
            logger.info("Reloading\n")
            try:
                p = subprocess.run(sys.argv)
                sys.exit(p.returncode)
            except KeyboardInterrupt:
                return


if __name__ == "__main__":
    settings = Settings.load_global()

    parser = argparse.ArgumentParser(description="Runs the server")
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
    parser.add_argument(
        "--no-reload", "-nr",
        action="store_true",
        help="If present disables auto-reloading"
    )
    args = parser.parse_args()

    reload = not args.no_reload and (args.reload or settings.get("reload"))
    asyncio.run(run_server(settings, args.host, args.port, reload))
