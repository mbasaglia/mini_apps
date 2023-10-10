import asyncio

from .settings import Settings, LogSource
from .service import Service
from .reloader import Reloader


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


class ServerTask:
    """
    Keeps track of a service and its related task
    """
    def __init__(self, service: Service):
        self.service = service
        self.taks = None

    def start(self):
        """
        Creates and starts the task for this service
        """
        coro = self.service.run()
        wrapped = coro_wrapper(coro, self.service)
        self.task = asyncio.create_task(wrapped, name=self.service.name)
        return self.task


class Server(LogSource):
    """
    Runs the server with all the bots and services
    """
    def __init__(self, settings: Settings):
        super().__init__("server")
        self.settings = settings
        self.services = {}
        self.tasks = []

    def add_service(self, service: Service):
        """
        Adds a service to the server
        """
        self.services[service.name] = ServerTask(service)

    def setup_run(self, host, port):
        database = self.settings.connect_database()

        http = self.settings.http_server(host, port)

        for app in self.settings.app_list:
            self.add_service(app)
            http.register_service(app)

        http.register_routes()
        self.add_service(http)

        self.tasks = []
        for task in self.services.values():
            self.tasks.append(task.start())

        return database

    async def run(self, host, port, reload):
        """
        Runs the server

        :return: True if the server needs to be reloaded
        """
        database = self.setup_run(host, port)

        try:
            if not reload:
                await asyncio.Future()
            else:
                reload = False
                server_path = self.settings.paths.server
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
            self.log.info("Shutting down")
            database.close()

            for task in self.tasks:
                self.log.debug("Stopping %s", task.get_name())
                task.cancel()

            await asyncio.wait(self.tasks, return_when=asyncio.ALL_COMPLETED)
            self.log.debug("All stopped")

            if reload:
                self.log.info("Reloading\n")
                return True

            return False
