import typing
import inspect
import dataclasses

from aiohttp.web_urldispatcher import Resource, PrefixedSubAppResource, PlainResource, StaticResource, DynamicResource

from mini_apps.http.utils import FileResource, NakedSubAppResource


def format_handler(handler):
    if inspect.isfunction(handler) or inspect.ismethod(handler):
        return "%s.%s" % (handler.__module__, handler.__qualname__)
    return str(handler)


@dataclasses.dataclass
class RouteInfo:
    path: str
    name: str
    handler_name: str
    resource: Resource
    children: typing.List["RouteInfo"] = dataclasses.field(default_factory=list)

    def __str__(self):
        return "%s%s -> %s" % (
            self.path,
            " (%s)" % self.name if self.name else "",
            self.handler_name
        )

    @classmethod
    def from_app(cls, app):
        return [
            cls.from_resource(resource)
            for resource in app.router.resources()
        ]

    @classmethod
    def from_resource(cls, resource: Resource):
        info = resource.get_info()
        if isinstance(resource, FileResource):
            return cls(info["prefix"], resource.name, info["file"], resource)
        elif isinstance(resource, PlainResource):
            return cls(info["path"], resource.name, format_handler(next(iter(resource._routes.values())).handler), resource)
        elif isinstance(resource, PrefixedSubAppResource):
            return cls(info["prefix"], resource.name, "app", resource, cls.from_app(info["app"]))
        elif isinstance(resource, StaticResource):
            return cls(info["prefix"], resource.name, info["directory"], resource)
        elif isinstance(resource, DynamicResource):
            return cls(info["formatter"], resource.name, format_handler(next(iter(resource._routes.values())).handler), resource)
        elif isinstance(resource, NakedSubAppResource):
            return cls(".", resource.name, "app", resource, cls.from_app(info["app"]))
        else:
            raise Exception("%s %s" % (resource, info))
