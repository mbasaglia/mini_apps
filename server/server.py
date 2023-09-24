#!/usr/bin/env python3
import asyncio

from mini_event.mini_event import MiniEventApp

if __name__ == "__main__":
    app = MiniEventApp.from_settings()
    asyncio.run(app.run())
