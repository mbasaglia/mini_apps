import asyncio
import math
import time

import hashids
import lottie
import lottie.utils.stripper

from . import models


id_encoder = hashids.Hashids("glaximini", alphabet="abcdefhkmnpqrstuvwxy34578")


def encode_id(id):
    args = [id]
    if id < 100:
        args.append(id % 10)

    return id_encoder.encode(*args)


def decode_id(id):
    return id_encoder.decode(id.lower())[0]


def sort_shapes(shapes):
    return reversed(shapes)


class Document:
    def __init__(self, model):
        super().__init__()
        self.clients = {}
        self.shapes = {}
        self.public_id = encode_id(model.id)
        self.model = model

        for db_shape in self.model.shapes:
            shape = Shape(db_shape.shape, db_shape.public_id, db_shape.props)
            shape._parent_id = db_shape.parent_id
            self.shapes[db_shape.public_id] = shape
            for dbkf in db_shape.keyframes:
                shape.keyframes[dbkf.time] = Keyframe(shape.id, dbkf.time, dbkf.props)

        for shape in self.shapes.values():
            if shape._parent_id:
                shape.set_parent(self.shapes[shape._parent_id])

    @classmethod
    def from_id(cls, id):
        model = models.Document.select().where(models.Document.id == id).first()
        if not model:
            try:
                model = models.Document.select().where(models.Document.id == decode_id(id)).first()
                if not model:
                    return None
            except Exception:
                return None
        return cls(model)

    @classmethod
    def from_data(cls, data):
        model = models.Document(url="", **data)
        model.save()
        return cls(model)

    # @classmethod
    # def from_url(cls, url):
    #     with curlopen(url) as resp:
    #         mime = resp.headers["content-type"]
    #         importer = None
    #         if mime == "appication/json" or mime == "application/gzip":
    #             importer = lottie.importers.importers.get("lottie")
    #         elif mime == "application/zip":
    #             importer = lottie.importers.importers.get("dotlottie")
    #         elif mime == "image/svg+xml":
    #             importer = lottie.importers.importers.get("svg")
    #         else:
    #             importer = lottie.importers.importers.get_from_filename(urllib.parse.urlparse(resp.url).path)
    #
    #         animation = importer.process(resp)
    #
    #     model = models.Document(url=url)
    #     load_animation(animation, model, "strip")

        return cls(model)

    def message_data(self):
        return {
            "id": self.public_id,
            "url": self.model.url,
            "width": self.model.width,
            "height": self.model.height,
            "fps": self.model.fps,
            "duration": self.model.duration,
            "start": self.model.start,
        }

    async def join(self, client):
        await client.send(type="document.open", **self.message_data(), id_prefix="%s-%s-" % (int(time.time()), client.user.telegram_id))

        for other in self.clients.values():
            await client.send(type="client.join", **other.to_json())

        for shape in self.shapes.values():
            if shape.alive:
                await client.send(**shape.to_command())
                for kf in shape.keyframes.values():
                    await client.send(**kf.to_command())

        for shape in self.shapes.values():
            if shape.parent:
                await client.send(**shape.parent_to_command())

        await client.send(type="document.loaded")

        client.document = self
        self.clients[client.id] = client
        models.UserDoc.get_or_create(telegram_id=client.user.telegram_id, document=self.model)

        await self.broadcast(type="client.join", skip=client.id, **client.to_json())

    async def leave(self, client):
        self.clients.pop(client.id)
        for other in self.clients.values():
            if client.user.telegram_id == other.user.telegram_id:
                return
        await self.broadcast(type="client.leave", id=client.user.telegram_id)

    async def broadcast(self, *, skip=None, **data):
        messages = []

        for client in self.clients.values():
            if client.id != skip:
                messages.append(client.send(**data))

        await asyncio.gather(*messages, return_exceptions=True)

    async def edit(self, client, command, data):
        self.model.lottie = None

        if command == "shape.add":
            if data["id"] in self.shapes:
                self.shapes[data["id"]].undelete()
            else:
                self.shapes[data["id"]] = Shape(**data)
        elif command == "shape.delete":
            self.shapes[data["id"]].delete()
        elif command == "shape.edit":
            shapes = []
            fail = False
            timestamp = data["timestamp"]
            for id in data["ids"]:
                shape = self.shapes.get(id)
                shapes.append(shape)
                if shape.alive:
                    if timestamp <= shape.last_modified:
                        fail = True
                        await client.send(
                            type="document.edit",
                            command="shape.edit",
                            data={
                                "ids": [shape.id],
                                "props": shape.props,
                                "timestamp": shape.last_modified,
                            }
                        )
            if fail:
                return

            for shape in shapes:
                shape.update(timestamp, data["props"])

        elif command == "keyframe.add":
            self.shapes[data["id"]].set_keyframe(data["time"], data["props"])
        elif command == "keyframe.delete":
            self.shapes[data["id"]].keyframes.pop(data["time"])
        elif command == "shape.parent":
            self.shapes[data["child"]].set_parent(self.shapes.get(data["parent"], None))

        # await self.broadcast(type="document.edit", command=command, data=data)

    def save(self):
        to_insert = []
        to_delete = []
        processed = set()

        self.cached_lottie()
        self.model.save()

        # Update existing
        for db_shape in self.model.shapes:
            processed.add(db_shape.public_id)
            if db_shape.public_id in self.shapes:
                local_shape = self.shapes[db_shape.public_id]
                if not local_shape.alive:
                    to_delete.append(db_shape.public_id)
                else:
                    db_shape.props = local_shape.props
                    db_shape.parent_id = local_shape.parent.id if local_shape.parent else None
                    db_shape.save()
            else:
                to_delete.append(db_shape.public_id)

        # Insert new
        for shape in self.shapes.values():
            if shape.alive and shape.id not in processed:
                to_insert.append(models.Shape(
                    public_id=shape.id,
                    props=shape.props,
                    document=self.model,
                    shape=shape.shape,
                    parent_id=shape.parent.id if shape.parent else None
                ))

        models.Shape.bulk_create(to_insert)

        # Delete old
        models.Shape.delete().where((models.Shape.document == self.model) & models.Shape.public_id.in_(to_delete)).execute()

        # Update keyframes
        shape_ids = {}
        for db_shape in models.Shape.select(models.Shape.id, models.Shape.public_id).where(models.Shape.document == self.model.id):
            shape_ids[db_shape.public_id] = db_shape.id

        models.Keyframe.delete().where(models.Keyframe.shape.in_(list(shape_ids.values()))).execute()

        kf_data = []
        for shape in self.shapes.values():
            if shape.alive:
                for kf in shape.keyframes.values():
                    kf_data.append(models.Keyframe(time=kf.time, props=kf.props, shape=shape_ids[shape.id]))

        models.Keyframe.bulk_create(kf_data)

    def cached_lottie(self):
        if self.model.lottie is None:
            anim = self.to_lottie()
            lottie.utils.stripper.heavy_strip(anim)
            self.model.lottie = anim.to_dict()
        return self.model.lottie

    def to_lottie(self):
        anim = lottie.objects.animation.Animation()
        anim.in_point = self.model.start
        anim.out_point = self.model.duration
        anim.framerate = self.model.fps
        anim.width = self.model.width
        anim.height = self.model.height

        layer = anim.add_layer(lottie.objects.layers.ShapeLayer())
        for shape in sort_shapes(self.shapes.values()):
            if shape.alive and not shape.parent:
                layer.shapes.append(shape.to_lottie())

        return anim


class Keyframe:
    def __init__(self, shape_id, time, props):
        self.shape_id = shape_id
        self.time = time
        self.props = props

    def to_command(self):
        return {
            "type": "document.edit",
            "command": "keyframe.add",
            "data": {
                "id": self.shape_id,
                "time": self.time,
                "props": self.props,
            }
        }


class ToLottieConverter:
    def __init__(self):
        self.shape = self.shape_type()

    def process(self, edit_shape):
        if len(edit_shape.keyframes) == 0:
            props = self.props(edit_shape.props)
            for name, val in props.items():
                getattr(self.shape, name).value = val
        else:
            base_props = self.props(edit_shape.props)
            for kf in sorted(edit_shape.keyframes.values(), key=lambda kf: kf.time):
                props = dict(base_props)
                try:
                    props.update(self.props(kf.props))
                except KeyError:
                    pass
                for name, val in props.items():
                    getattr(self.shape, name).add_keyframe(kf.time, val)

        return self.shape


class FillConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.Fill

    def props(self, props):
        return FillConverter.process_color(props["fill"])

    @staticmethod
    def process_color(color):
        color = lottie.utils.color.color_from_hex(color)
        opacity = color.alpha * 100
        color.alpha = 1
        return {
            "color": color,
            "opacity": opacity,
        }


class StrokeConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.Stroke

    def props(self, props):
        out = FillConverter.process_color(props["stroke"])
        out["width"] = props["stroke_width"]
        return out


class EllipseConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.Ellipse

    def props(self, props):
        return {
            "position": lottie.NVector(props["cx"], props["cy"]),
            "size": lottie.NVector(props["rx"], props["ry"]) * 2
        }


class RectangleConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.Rect

    def props(self, props):
        top = props["top"]
        left = props["left"]
        width = props["width"]
        height = props["height"]
        return {
            "position": lottie.NVector(left + width / 2, top + height / 2),
            "size": lottie.NVector(width, height),
        }


class BezierConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.Path

    def props(self, props):
        bez = lottie.objects.bezier.Bezier()
        if len(props.get("bezier", [])) > 0:
            points = list(map(lambda x: lottie.NVector(*x), props["bezier"]))
            bez.vertices.append(points[0])
            bez.in_tangents.append(lottie.NVector(0, 0))
            for i in range(3, len(points), 3):
                bez.vertices.append(points[i])
                bez.out_tangents.append(points[i-2]-points[i-3])
                bez.in_tangents.append(points[i-1]-points[i])
            bez.out_tangents.append(lottie.NVector(0, 0))

        return {
            "shape": bez
        }


class TransformConverter(ToLottieConverter):
    shape_type = lottie.objects.shapes.TransformShape

    def props(self, props):
        return {
            "position": lottie.NVector(*props["position"]),
            "anchor_point": lottie.NVector(*props["anchor"]),
            "scale": lottie.NVector(*props["scale"]) * 100,
            "rotation": props["rotation"] * 180 / math.pi
        }


class Shape:
    def __init__(self, shape, id, props):
        self.shape = shape
        self.id = id
        self.props = props
        self.deleted = False
        self.parent_deleted = False
        self.keyframes = {}
        self.last_modified = 0
        self.parent = None
        self.children = []

    def to_command(self):
        return {
            "type": "document.edit",
            "command": "shape.add",
            "data": {
                "id": self.id,
                "shape": self.shape,
                "props": self.props
            }
        }

    def parent_to_command(self):
        return {
            "type": "document.edit",
            "command": "shape.parent",
            "data": {
                "child": self.id,
                "parent": self.parent.id
            }
        }

    def set_keyframe(self, time, props):
        self.keyframes[time] = Keyframe(self.id, time, props)

    def to_lottie(self):
        group = lottie.objects.shapes.Group()
        group.name = self.id

        if self.shape == "group":
            trans = TransformConverter().process(self)
            group.shapes = [
                c.to_lottie() for c in reversed(self.children)
                if c.alive
            ] + [trans]
            return group

        if self.shape == "ellipse":
            conv = EllipseConverter()
        elif self.shape == "rectangle":
            conv = RectangleConverter()
        elif self.shape == "bezier":
            conv = BezierConverter()
        else:
            return group

        group.add_shape(conv.process(self))
        group.add_shape(StrokeConverter().process(self))
        group.add_shape(FillConverter().process(self))

        return group

    def update(self, timestamp, props):
        if timestamp <= self.last_modified:
            return False

        self.last_modified = timestamp
        self.props.update(**props)
        return True

    def set_parent(self, parent):
        if self.parent and self in self.parent.children:
            self.parent.children.pop(self.parent.children.index(self))

        self.parent = parent

        if self.parent and self not in self.parent.children:
            self.parent.children.append(self)

    def delete(self):
        self.deleted = True
        self._mark_parent_deleted()

    def undelete(self):
        self.deleted = False
        self._mark_parent_undeleted()

    def _mark_parent_deleted(self):
        for child in self.children:
            child.parent_deleted = True
            if not child.deleted:
                child._mark_parent_deleted()

    def _mark_parent_undeleted(self):
        for child in self.children:
            child.parent_deleted = False
            if not child.deleted:
                child._mark_parent_undeleted()

    @property
    def alive(self):
        return not self.deleted and not self.parent_deleted
