import asyncio
import pathlib
from .settings import LogSource


class Reloader(LogSource):
    """
    Utility to reload scripts when the sources change
    """
    def __init__(self, path: pathlib.Path, globs=["**/*.py", "*/*.json"]):
        super().__init__("reloader")
        self.path = path
        self.globs = globs
        self.task = None

    def watched_files(self):
        for pattern in self.globs:
            yield from self.path.glob(pattern)

    def most_recent(self):
        most_recent = 0
        most_recent_file = None

        for file in self.watched_files():
            mod_time = file.stat().st_mtime
            if mod_time > most_recent:
                most_recent = mod_time
                most_recent_file = file

        return most_recent, most_recent_file

    async def watch(self):
        self.log.info("Watching %s", self.path)
        last_known_modification = self.most_recent()[0]

        while True:
            try:
                most_recent, file = self.most_recent()
                if last_known_modification < most_recent:
                    self.log.debug("%s was modified", file)
                    return True
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                return False
            except asyncio.exceptions.CancelledError:
                return False
