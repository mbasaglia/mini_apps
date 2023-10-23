import asyncio
import logging
from .settings import LogSource


class Reloader(LogSource):
    """
    Utility to reload scripts when the sources change
    """
    def __init__(self, paths, globs=["**/*.py", "**/*.json"], polling_interval=1):
        super().__init__("reloader")
        self.paths = paths
        self.globs = globs
        self.task = None
        self.polling_interval = polling_interval

    def watched_files(self):
        """
        Generator returing all files being watched
        """
        for path in self.paths:
            if path.is_file():
                yield path
            elif path.is_dir():
                for pattern in self.globs:
                    yield from path.glob(pattern)

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
        """
        Coroutine returning True if the files have changed on disk
        """
        if self.log.level <= logging.INFO:
            for path in self.paths:
                self.log.info("Watching %s", path)
        last_known_modification = self.most_recent()[0]

        while True:
            try:
                most_recent, file = self.most_recent()
                if last_known_modification < most_recent:
                    self.log.debug("%s was modified", file)
                    return True
                await asyncio.sleep(self.polling_interval)
            except KeyboardInterrupt:
                return False
            except asyncio.exceptions.CancelledError:
                return False
