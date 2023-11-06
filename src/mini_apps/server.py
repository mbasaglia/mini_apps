import asyncio

from .settings import Settings, LogSource
from .service import Service
from .reloader import Reloader
from .http import HttpServer


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
        self.task = None
        self.started = False

    def start(self):
        """
        Creates and starts the task for this service
        """
        self.started = True
        coro = self.service.run()
        wrapped = coro_wrapper(coro, self.service)
        self.task = asyncio.create_task(wrapped, name=self.service.name)
        return self.task

    async def stop(self):
        """
        Stops the service
        """
        await self.service.stop()
        self.started = False


class Server(LogSource):
    """
    Runs the server with all the bots and services
    """
    def __init__(self, settings: Settings):
        super().__init__("server")
        self.settings = settings
        self.services = {}
        self.tasks = []
        self.providers = {}

    def add_service(self, service: Service):
        """
        Adds a service to the server
        """
        self.services[service.name] = ServerTask(service)
        service.server = self

        for prov in service.provides():
            self.providers[prov] = service

        for cons in set(service.consumes()):
            self.providers[cons].register_consumer(cons, service)

    def load_services(self, host, port):
        # Register all the services
        for app in self.settings.app_list:
            if isinstance(app, HttpServer):
                if host:
                    app.host = host
                if port:
                    app.port = port
            self.add_service(app)

    def get_server_task(self, service):
        if isinstance(service, ServerTask):
            return service
        if isinstance(service, Service):
            return self.services[service.name]
        return self.services[service]

    def start_service(self, service):
        self.tasks.append(self.get_server_task(service).start())

    async def stop_service(self, service):
        task = self.get_server_task(service)
        if task.started:
            self.log.debug("Stopping %s", task.service.name)
            await task.stop()

    async def run(self, host: str, port: int, reload: bool, start: set):
        """
        Runs the server

        :return: True if the server needs to be reloaded
        """
        self.load_services(host, port)

        # Start the tasks
        for task in self.services.values():
            if task.service.autostart or task.service.name in start:
                self.tasks.append(task.start())

        try:
            if not reload:
                await asyncio.Future()
            else:
                reload = False
                server_path = self.settings.paths.server
                paths = [
                    server_path / "mini_apps",
                    server_path / "server.py",
                    self.settings.paths.settings,
                ]
                reloader = Reloader(paths)
                reload = await reloader.watch()

        except KeyboardInterrupt:
            pass

        finally:
            self.log.info("Shutting down")

            for task in self.services.values():
                await self.stop_service(task)

            done, pending = await asyncio.wait(self.tasks, return_when=asyncio.ALL_COMPLETED, timeout=1)

            # Cancel misbehaving tasks
            if pending:
                for task in pending:
                    self.log.debug("Force stopping %s", task.get_name())
                    task.cancel()

                await asyncio.wait(self.tasks, return_when=asyncio.ALL_COMPLETED, timeout=1)

            self.log.debug("All stopped")

            if reload:
                self.log.info("Reloading\n")
                return True

            return False
