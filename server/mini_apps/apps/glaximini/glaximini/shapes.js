import { Point, Matrix, BoundingBox, Polygon } from "./math.js";
import { Bezier } from "./bezier.js";
import { lerp_hex, hex_to_rgb } from "./color.js"

function value_to_lottie(value, make_array = false)
{
    if ( typeof value == "number" )
    {
        if ( make_array )
            return [value];
        return value;
    }
    else if ( typeof value == "string" && value[0] == "#" )
    {
        return hex_to_rgb(value, 1/255);
    }
    else if ( value instanceof Point )
    {
        return [value.x, value.y];
    }
    else if ( value instanceof Bezier )
    {
        let lottie_bezier = {
            c: false,
            v: [],
            i: [],
            o: [],
        };

        if ( value.segments.length == 0 )
            return lottie_bezier;

        let flat = value.toJSON();

        let closed = flat[0].is_equal(flat[flat.length-1]);

        if ( closed )
        {
            lottie_bezier.c = true;
            flat.pop();
            lottie_bezier.i.push(value_to_lottie(flat.pop().sub(flat[0])));
        }
        else
        {
            lottie_bezier.i.push([0, 0]);
        }

        for ( let i = 0; i < value.segments.length; i += 3 )
        {
            let pos = flat[i];
            lottie_bezier.o.push(value_to_lottie(pos));
            lottie_bezier.o.push(value_to_lottie(flat[i+1].sub(pos)));
            lottie_bezier.i.push(value_to_lottie(flat[i+2].sub(pos)));
        }

        if ( !closed )
            lottie_bezier.o.push([0, 0]);

        return lottie_bezier;
    }
    else
    {
        return value;
    }
}

class LottieConverterProperty
{
    constructor(input_props, lottie_name, conversion = x => x)
    {
        this.keyframes = [];
        this.value = null;
        this.input_props = input_props;
        this.conversion = conversion;
        this.lottie_name = lottie_name;
    }

    extract_value(props, make_array)
    {
        let vals = [];
        for ( let prop of this.input_props )
            vals.push(props[prop]);
        return value_to_lottie(this.conversion(...vals, make_array));
    }

    process_keyframe(keyframe, props)
    {
        this.keyframes.push({...keyframe, s: this.extract_value(props, true)});
    }

    process_value(props)
    {
        this.value = this.extract_value(props, false);
    }

    to_lottie()
    {
        if ( this.keyframes.length )
            return {"a": 1, "k": this.keyframes};
        return {"a": 0, "k": this.value};
    }
}

class LottieConverter
{
    constructor(properties)
    {
        this.properties = {};
        for ( let prop of properties )
            this.properties[prop.lottie_name] = prop;
    }

    process_keyframe(keyframe, props)
    {
        for ( let prop of Object.values(this.properties) )
            prop.process_keyframe(keyframe, props);
    }

    process_value(props)
    {
        for ( let prop of Object.values(this.properties) )
            prop.process_value(props);
    }

    process_object(object)
    {
        this.process_value(object.props);
        for ( let kf of object.timeline.keyframes )
        {
            let lkf = {
                t: this.time,
                o: {x: 0, y: 0},
                i: {x: 1, y: 1},
            };
            this.process_keyframe(lkf, kf.props);
        }

        return this;
    }

    to_lottie(init={})
    {
        let lottie_object = {...init};
        for ( let prop of Object.values(this.properties) )
            lottie_object[prop.lottie_name] = prop.to_lottie();
        return lottie_object;
    }
}

export class EditorObject
{
    constructor(id, editor)
    {
        editor.objects[id] = this;
        this.id = id;
        this.parent = null;
        this.editor = editor;
        this.frame = 0;
        this.props = {};
        this.timeline = new Timeline();
    }

    enter_frame(frame)
    {
        this.frame = frame;
        let props = this.timeline.props_at(frame);
        if ( props != null )
            this.assign_props(props);
    }

    assign_props(props)
    {
        this.filter_props(props);
        for ( let [k, v] of Object.entries(props) )
            this.props[k] = v;

        this.on_props_updated();
    }

    add_keyframe(time, props)
    {
        let prop_copy = {...props};
        this.filter_props(prop_copy);
        this.timeline.add_keyframe(time, prop_copy);
    }

    remove_keyframe(time)
    {
        this.timeline.remove_keyframe(time);
    }

    to_lottie()
    {
        return this.to_lottie_converter().process_object(this).to_lottie();
    }

    to_lottie_properties()
    {
        return [];
    }

    to_lottie_converter()
    {
        return new LottieConverter(this.to_lottie_properties());
    }

    filter_props(props) {}

    paint(context) {}

    bounding_box(include_stroke = false){}

    contains(pos){ return false; }

    on_props_updated() {}

    move(dx, dy) {}
}


export class GroupObject extends EditorObject
{
    constructor(id, editor)
    {
        super(id, editor)
        this.children = [];
        this.props = {
            anchor: new Point(0, 0),
            position: new Point(0, 0),
            rotation: 0,
            scale: new Point(1, 1)
        };
        this.matrix = new Matrix();
        this.inverted_matrix = new Matrix()
    }

    to_lottie()
    {
        let lottie_object = {
            ty: "gr",
            it: []
        };

        for ( let child of this.children )
            lottie_object.it.push(child.to_lottie());

        lottie_object.it.push(this.to_lottie_converter().process_object(this).to_lottie({
            ty: "tr",
            o: {a: 0, k: 100}
        }));

        return lottie_object;
    }

    to_lottie_properties()
    {
        return [
            new LottieConverterProperty(["anchor"], "a"),
            new LottieConverterProperty(["position"], "p"),
            new LottieConverterProperty(["rotation"], "r"),
            new LottieConverterProperty(["scale"], "s", p => p.mul(100)),
        ];
    }

    to_lottie_layer(ip, op)
    {
        let lottie_object = {
            ty: 4,
            ip: ip,
            op: op,
            st: 0,
            sr: 1,
            ks: this.to_lottie_converter().process_object(this).to_lottie({
                o: {a: 0, k: 100}
            }),
            shapes: []
        };

        for ( let child of this.children )
            lottie_object.shapes.push(child.to_lottie());

        return lottie_object;
    }

    insert_child(obj)
    {
        // TODO preserve order on insert/remove
        obj.parent = this;
        this.children.push(obj);
    }

    remove_child(obj)
    {
        this.children = this.children.filter(c => c.id != obj.id);
    }

    on_props_updated()
    {
        this._refresh_matrix();
    }

    _refresh_matrix()
    {
        this.matrix = new Matrix();
        this.matrix.translate(-this.props.anchor.x, -this.props.anchor.y);
        this.matrix.scale(this.props.scale.x, this.props.scale.y);
        this.matrix.rotate(-this.props.rotation);
        this.matrix.translate(this.props.position.x, this.props.position.y);

        this.inverted_matrix = this.matrix.inverted();
    }

    _parent_to_local(pos)
    {
        return new Point(this.inverted_matrix.map(pos.x, pos.y));
    }

    filter_props(props)
    {
        for ( let prop of ["anchor", "position", "scale"] )
        {
            if ( props[prop] )
                props[prop] = new Point(props[prop]);
        }
    }

    move(dx, dy)
    {
        this.position.x += dx;
        this.position.y += dy;
        this._refresh_matrix();
    }

    object_at(pos)
    {
        return this;
    }

    child_at(pos)
    {
        const local_pos = this._parent_to_local(pos);

        for ( let child of this.children )
            if ( child.contains(local_pos) )
                return child;

        return null;
    }

    contains(pos)
    {
        return this.child_at(pos) != null;;
    }

    paint(context)
    {
        context.save();
        context.transform(...this.matrix.to_canvas())

        for ( let child of this.children )
            child.paint(context);

        context.restore();
    }

    bounding_box(include_stroke = false)
    {
        if ( this.children.length == 0 )
            return new BoundingBox(-1, -1, -1, -1);

        let box = null;

        if ( this.children.length == 1 )
        {
            box = this.children[0].bounding_box(include_stroke);
        }
        else
        {
            box = new BoundingBox();
            for ( let i = 0; i < this.children.length; i++ )
                box.include(this.children[i].bounding_box(include_stroke));
        }

        return new Polygon(box.corners.map(p => new Point(this.matrix.map(p.x, p.y))));
    }

    enter_frame(frame)
    {
        super.enter_frame(frame);
        for ( let child of this.children )
            child.enter_frame(frame);
    }

    get_style()
    {
        for ( let child of this.children )
        {
            let style = child.get_style();
            if ( style )
                return style;
        }

        return null;
    }
}

export class Layer extends GroupObject
{
    object_at(pos)
    {
        return this.child_at(pos);
    }

    to_lottie_animation(w, h, ip, op)
    {
        let lottie_object = {
            w: w,
            h: h,
            ip: ip,
            op: op,
            fr: 60,
            layers: []
        };

        for ( let child of this.children )
        {
            lottie_object.layers.push(child.to_lottie_layer(ip, op));
        }

        return lottie_object;

    }
}

function point_in_rect(pos, rect, pad_x = 0, pad_y = 0)
{
    return pos.x >= rect.left - pad_x && pos.x <= rect.left + rect.width + pad_x &&
           pos.y >= rect.top - pad_y && pos.y <= rect.top + rect.height + pad_y;
}


function point_in_ellipse(pos, cx, cy, rx, ry)
{
    let dx = pos.x - cx;
    let dy = pos.y - cy;
    return (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1;
}


class Keyframe
{
    constructor(time, props)
    {
        this.time = time;
        this.props = props;
    }

    interpolate(time, other)
    {
        if ( !other || other.time == this.time )
            return this.props;

        let props = {};
        let factor = (time - this.time) / (other.time - this.time);

        for ( let [name, val] of Object.entries(this.props) )
        {
            props[name] = this.lerp(factor, val, other.props[name]);
        }

        return props;
    }

    lerp(factor, a, b)
    {
        if ( a == b )
            return a;
        if ( typeof a == "number" )
            return a * (1-factor) + b * factor;
        else if ( typeof a == "string" && a[0] == "#" )
            return lerp_hex(factor, a, b);
        else if ( a instanceof Bezier )
            return a.lerp(factor, b);
        else if ( a instanceof Point )
            return a.lerp(factor, b);
        return a;
    }
}

class Timeline
{
    constructor()
    {
        this.keyframes = [];
    }

    add_keyframe(time, props)
    {
        let pos = this.keyframes.findIndex(kf => kf.time >= time);
        if ( pos == -1 )
            this.keyframes.push(new Keyframe(time, props));
        else if ( this.keyframes[pos].time == time )
            this.keyframes[pos].props = props;
        else
            this.keyframes.splice(pos, 0, new Keyframe(time, props));
    }

    props_at(time)
    {
        if ( !this.keyframes.length )
            return null;

        let pos = this.keyframes.findIndex(kf => kf.time >= time);
        if ( pos == -1 )
            return this.keyframes[this.keyframes.length-1].props;
        else if ( pos == 0 )
            return this.keyframes[0].props;

        return this.keyframes[pos-1].interpolate(time, this.keyframes[pos]);
    }

    remove_keyframe(time)
    {
        let pos = this.keyframes.findIndex(kf => kf.time == time);
        if ( pos != -1 )
            this.keyframes.splice(pos, 1);
    }
}

class EditorShape extends EditorObject
{
    constructor(id, editor)
    {
        super(id, editor);
        this.props = {
            fill: "#000000",
            stroke: "#000000",
            stroke_width: 4,
        };
        this.lottie_ty = "";
    }

    to_lottie()
    {
        let converter = this.to_lottie_converter().process_object(this);
        let obj = converter.to_lottie({ty: this.lottie_ty});
        let group = {
            ty: "gr",
            it: [
                obj,
                {
                    ty: "st",
                    o: {a: 0, k: 100},
                    c: obj._stroke,
                    w: obj._stroke_width,
                },
                {
                    ty: "fl",
                    o: {a: 0, k: 100},
                    c: obj._fill,
                },
                {
                    ty: "tr",
                    o: {a: 0, k: 100},
                },
            ]
        };

        delete obj._fill;
        delete obj._stroke;
        delete obj._stroke_width;
        return group;
    }

    to_lottie_layer(ip, op)
    {
        let lottie_object = {
            ty: 4,
            ip: ip,
            op: op,
            st: 0,
            sr: 1,
            ks: {},
            shapes: [this.to_lottie()]
        };
        return lottie_object;
    }

    to_lottie_properties()
    {
        return [
            new LottieConverterProperty(["fill"], "_fill"),
            new LottieConverterProperty(["stroke"], "_stroke"),
            new LottieConverterProperty(["stroke_width"], "_stroke_width"),
        ];
    }

    set_fill(fill, opacity)
    {
        this.fill = fill;
        this.fill_opacity = opacity;
    }

    set_stroke(width, stroke, opacity)
    {
        this.stroke_width = width;
        this.stroke = stroke;
        this.stroke_opacity = opacity;
    }

    paint(context)
    {
        context.fillStyle = this.props.fill;
        context.strokeStyle = this.props.stroke;
        context.lineWidth = this.props.stroke_width;

        context.beginPath();
        this.draw_path(context);
        context.fill("evenodd");
        if ( this.props.stroke_width > 0 )
            context.stroke();
    }

    draw_path(context) {}


    get_style()
    {
        return this.props;
    }

    bounding_box(include_stroke)
    {
        let bb = this._on_bounding_box();
        if ( include_stroke && this.props.stroke.substr(-2) != "00" )
            bb.expand(this.props.stroke_width / 2);
        return bb;
    }

    gather_styled_objects(objects)
    {
        objects.push(this);
    }
}


export class EllipseShape extends EditorShape
{
    constructor(id, editor)
    {
        super(id, editor);
        this.props.cx = 0;
        this.props.cy = 0;
        this.props.rx = 0;
        this.props.ry = 0;
        this.lottie_ty = "el";
    }

    draw_path(context)
    {
        context.ellipse(this.props.cx, this.props.cy, this.props.rx, this.props.ry, 0, 0, 2 * Math.PI);
    }


    _on_bounding_box()
    {
        return new BoundingBox(
            this.props.cx - this.props.rx,
            this.props.cy - this.props.ry,
            this.props.rx * 2,
            this.props.ry * 2,
        );
    }

    contains(pos)
    {
        return point_in_ellipse(pos, this.props.cx, this.props.cy, this.props.rx, this.props.ry);
    }

    to_lottie_properties()
    {
        return super.to_lottie_properties().concat([
            new LottieConverterProperty(["cx", "cy"], "p", (x, y) => [x, y]),
            new LottieConverterProperty(["rx", "ry"], "s", (x, y) => [x * 2, y * 2]),
        ]);
    }
}

export class RectangleShape extends EditorShape
{
    constructor(id, editor)
    {
        super(id, editor);
        this.props.top = 0;
        this.props.left = 0;
        this.props.width = 0;
        this.props.height = 0;
        this.lottie_ty = "rc";
    }

    draw_path(context)
    {
        context.rect(this.props.left, this.props.top, this.props.width, this.props.height);
    }

    _on_bounding_box()
    {
        return new BoundingBox(this.props.left, this.props.top, this.props.width, this.props.height);
    }

    contains(pos)
    {
        return point_in_rect(pos, this.props);
    }

    to_lottie_properties()
    {
        return super.to_lottie_properties().concat([
            new LottieConverterProperty(
                ["top", "left", "width", "height"], "p",
                (t, l, w, h) => [l + w/2, t + h/2]
            ),
            new LottieConverterProperty(["width", "height"], "s", (x, y) => [x, y]),
        ]);
    }
}

export class BezierShape extends EditorShape
{
    constructor(id, editor)
    {
        super(id, editor);
        this.props.bezier = new Bezier();
        this.bbox = null;
        this.lottie_ty = "sh";
    }

    filter_props(props)
    {
        if ( Array.isArray(props.bezier) )
            props.bezier = Bezier.fromJSON(props.bezier);
    }

    on_props_updated()
    {
        this.bbox = null;
    }

    _on_bounding_box()
    {
        if ( this.bbox == null )
            this.bbox = this.props.bezier.bounding_box();
        return this.bbox.copy();
    }

    contains(pos)
    {
        return this.props.bezier.contains_point(pos);
    }

    draw_path(context)
    {
        this.props.bezier.draw_path(context);
    }

    to_lottie_properties()
    {
        return super.to_lottie_properties().concat([
            new LottieConverterProperty("bezier", "ks")
        ]);
    }
}
