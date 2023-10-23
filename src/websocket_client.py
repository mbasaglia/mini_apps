#!/usr/bin/env python3
import argparse
import asyncio
import sys

import websockets


async def connect_stdin():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def stdin(websocket):
    reader = await connect_stdin()
    while True:
        try:
            raw = await reader.readuntil(b"\n")
            line = raw.decode("utf-8")
            print("> %s" % line)
            await websocket.send(line)
        except (KeyboardInterrupt, asyncio.exceptions.IncompleteReadError):
            break

    await websocket.disconnect()


async def connection(websocket):
    while True:
        try:
            data = await websocket.recv()
            print("< %s" % data)
        except KeyboardInterrupt:
            return
        except websockets.exceptions.ConnectionClosed:
            print("Disconnected")
            return


async def run_client(url):
    print("Connecting to %s" % url)
    async with websockets.connect(url) as websocket:
        tasks = [
            asyncio.create_task(connection(websocket)),
            asyncio.create_task(stdin(websocket))
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()


parser = argparse.ArgumentParser(description="Manually sends websocket data")
parser.add_argument(
    "url",
    type=str,
    default="ws://localhost:2537/wss/",
    nargs="?",
    help="Websocket URL"
)

if __name__ == "__main__":
    args = parser.parse_args()

    asyncio.run(run_client(args.url))
