from .settings import LogSource


class Service(LogSource):
    """
    Abstract class for services that can run on the server
    """

    async def run(self):
        """
        Should run the service until disconnected
        """
        raise NotImplementedError()
