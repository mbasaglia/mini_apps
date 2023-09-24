#!/usr/bin/env python3
import asyncio
import websockets

from mini_event.mini_event import MiniEventApp


if __name__ == "__main__":
    app = MiniEventApp.from_settings()

    database = app.connect()

    try:
        asyncio.run(app.run(app.settings["hostname"], app.settings["port"]))
    except KeyboardInterrupt:
        pass
    finally:
        database.close()
