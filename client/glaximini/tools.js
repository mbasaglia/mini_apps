import { EllipseShape, RectangleShape, BezierShape } from "./shapes.js"
import { Point } from "./math.js"
import { Bezier, BezierSegment } from "./bezier.js"
import { ShapeAddCommand } from "./command.js"

class EditorTool
{
    constructor(slug, name, command_stack)
    {
        this.slug = slug;
        this.name = name;
        this.command_stack = command_stack;
    }

    on_mouse_down(ev)
    {
    }

    on_mouse_move(ev)
    {
    }

    on_mouse_up(ev)
    {
    }

    on_activate()
    {
    }

    on_deactivate()
    {
    }

    get editor()
    {
        return this.command_stack.editor;
    }

    install(editor)
    {
        this.on_install(editor);
        editor.tools[this.slug] = this;
        if ( !editor.tool )
            editor.tool = this;
    }

    on_install(editor)
    {
    }

    draw_foreground(context)
    {}

    on_edit()
    {}

    on_enter_frame(ev)
    {}

    on_selected(shape)
    {}

}

export class DragTool extends EditorTool
{
    constructor(slug, name, command_stack)
    {
        super(slug, name, command_stack);
        this.dragging = false;
        this.drag_start = {x:0, y: 0};
        this.drag_last = this.drag_start;
    }

    _event(ev, pos)
    {
        return new DrawDragEvent(ev, this.editor, pos);
    }

    on_mouse_down(ev)
    {
        ev.stopPropagation();
        this.dragging = true;
        this.drag_last = this.drag_start = this.editor.mouse_event_pos(ev);
        this.on_drag_start(this._event(ev, this.drag_start));
    }

    on_mouse_move(ev)
    {
        if ( this.dragging )
        {
            let pos = this.editor.mouse_event_pos(ev)
            this.on_drag(this._event(ev, pos));
            this.drag_last = pos;
        }
    }

    on_mouse_up(ev)
    {
        ev.stopPropagation();
        if ( this.dragging )
        {
            this.dragging = false;
            this.on_drag_end(this._event(ev, this.editor.mouse_event_pos(ev)));
        }
    }

    on_drag_start(ev)
    {
    }

    on_drag(ev)
    {
    }

    on_drag_end(ev)
    {

    }

    on_deactivate()
    {
        if ( this.dragging )
        {
            this.dragging = false;
            this.on_drag_end(this.drag_last);
        }
    }
}

class DrawDragEvent
{
    constructor(ev, editor, pos)
    {
        this.editor = editor;
        this.pos = pos
        this.event = ev;
    }
}

export class EllipseTool extends DragTool
{
    constructor(command_stack)
    {
        super("ellipse", "Ellipse", command_stack);
    }

    on_drag_start(ev)
    {
        this.shape = null;
    }

    on_drag(ev)
    {
        if ( !this.shape )
        {
            let cmd = new ShapeAddCommand(
                "ellipse",
                {
                    cx: this.drag_start.x,
                    cy: this.drag_start.y,
                    ...ev.editor.current_style,
                }
            );
            this.command_stack.push(cmd);
            this.shape = cmd.data.id;
        }

        this.command_stack.edit_command(this.shape, {
            cx: (ev.pos.x + this.drag_start.x) / 2,
            cy: (ev.pos.y + this.drag_start.y) / 2,
            rx: Math.abs((ev.pos.x - this.drag_start.x) / 2),
            ry: Math.abs((ev.pos.y - this.drag_start.y) / 2),
        }, false);
    }

    on_drag_end(ev)
    {
        if ( this.shape )
        {
            this.editor.select_shape(this.shape);
            this.command_stack.commit();
            this.shape = null;
        }
    }

    on_install(editor)
    {
        editor.shape_types[this.slug] = EllipseShape;
    }
}


export class RectangleTool extends DragTool
{
    constructor(command_stack)
    {
        super("rectangle", "Rectangle", command_stack);
    }

    on_drag_start(ev)
    {
        this.shape = null;
    }

    on_drag(ev)
    {
        if ( !this.shape )
        {
            let cmd = new ShapeAddCommand(
                "rectangle",
                {
                    left: this.drag_start.x,
                    top: this.drag_start.y,
                    ...ev.editor.current_style,
                }
            );
            this.command_stack.push(cmd);
            this.shape = cmd.data.id;
        }

        let w = ev.pos.x - this.drag_start.x;
        let h = ev.pos.y - this.drag_start.y;
        let x = this.drag_start.x;
        let y = this.drag_start.y;

        if ( w < 0 )
        {
            x = this.drag_start.x + w;
            w = -w;
        }

        if ( h < 0 )
        {
            y = this.drag_start.y + h;
            h = -h;
        }

        this.command_stack.edit_command(this.shape, {
            left: x,
            top: y,
            width: w,
            height: h,
        }, false);
    }

    on_drag_end(ev)
    {
        if ( this.shape )
        {
            this.editor.select_shape(this.shape);
            this.command_stack.commit();
            this.shape = null;
        }
    }

    on_install(editor)
    {
        editor.shape_types[this.slug] = RectangleShape;
    }
}


const HandleShape = {
    Circle: 1,
    Diamond: 2,
};

const HandleColors = {
    Normal: "#00C6FF",
    Highlight: "#B0E8FD",
    Drag: "#FFFFFF",
};

export class EditHandle
{
    constructor(stack, shape, lock_x, lock_y, handle_shape = HandleShape.Circle, radius = 8)
    {
        this.stack = stack;
        this.shape = shape;
        this.x = 0;
        this.y = 0;
        this.lock_x = lock_x;
        this.lock_y = lock_y;
        this.dragged = false;
        this.radius = radius;
        this.handle_shape = handle_shape;
        this.colors = HandleColors;
        this.drag_offset = {x: 0, y: 0};
    }

    draw(context, highlight)
    {
        if ( this.dragged )
        {
            context.strokeStyle = this.colors.Drag;
            context.fillStyle = this.colors.Normal;
        }
        else if ( highlight )
        {
            context.strokeStyle = this.colors.Highlight;
            context.fillStyle = this.colors.Drag;
        }
        else
        {
            context.strokeStyle = this.colors.Normal;
            context.fillStyle = this.colors.Drag;
        }

        context.lineWidth = 1;

        context.beginPath();

        if ( this.handle_shape == HandleShape.Circle )
        {
            context.ellipse(this.x, this.y, this.radius, this.radius, 0, 0, 2 * Math.PI);
        }
        else if ( this.handle_shape == HandleShape.Diamond )
        {
            context.moveTo(this.x - this.radius, this.y);
            context.lineTo(this.x, this.y - this.radius);
            context.lineTo(this.x + this.radius, this.y);
            context.lineTo(this.x, this.y + this.radius);
            context.closePath();
        }

        context.fill();
        context.stroke();
    }

    drag_start(pos = null)
    {
        this.dragged = true;

        if ( pos )
            this.drag_offset = {x: pos.x - this.x, y: pos.y - this.y};
        else
            this.drag_offset = {x: 0, y: 0};
    }

    drag(ev)
    {
        let x = ev.pos.x - this.drag_offset.x;
        let y = ev.pos.y - this.drag_offset.y;

        if ( this.lock_x )
            x = this.x;
        else if ( this.lock_y )
            y = this.y;

        let props = this.on_drag(x, y);

        if ( props != null )
            this.stack.edit_command(this.shape.id, props, false);
    }

    drag_end()
    {
        this.dragged = false;
        this.stack.commit();
    }

    under(pos)
    {
        return Math.hypot(this.x - pos.x, this.y - pos.y) <= this.radius;
    }
}

EditHandle.Shape = HandleShape;
EditHandle.Colors = HandleColors;


export class BezierTool extends DragTool
{
    constructor(command_stack)
    {
        super("bezier", "Bezier", command_stack);

        this.bezier = null;
        this.first_point = new Point();

        this.point = new Point();
        this.tan_in = new Point();
        this.tan_out = new Point();
        this.next_tan_out = new Point();

        this.handle = new EditHandle(null, null, true, true);
        this.states = {
            Open: 1,
            Mid: 2,
            Close: 3,
        }
        this.state = this.states.Open;
    }

    on_drag_start(ev)
    {
        if ( !this.bezier )
        {
            // Create new bezier
            this.state = this.states.Open;
            let p = new Point(this.drag_start);
            this.bezier = new Bezier();
            this.point = p;
            this.tan_in = p;
            this.tan_out = p;
            this.next_tan_out = p;
            this.first_point = p;
            this.bezier.add_segment(p, p, p, p);
            this.handle.x = p.x;
            this.handle.y = p.y;
        }
        else
        {
            // Closing the bezier or dragging the last point tangent
            if ( this.handle.dragged )
            {
                this.point = this.first_point;
                this.state = this.states.Close;
            }
            else
            {
                this.point = new Point(this.drag_start);
                this.state = this.states.Mid;
            }

            this.next_tan_out = this.point;
            this.tan_in = this.point;
        }
    }

    on_mouse_move(ev)
    {
        super.on_mouse_move(ev);

        if ( !this.dragging && this.bezier )
        {
            // We already have the last segment, just update tan_in and point
            let pos = new Point(this.editor.mouse_event_pos(ev));
            this.handle.dragged = this.handle.under(pos);
            if ( this.state != this.states.Close )
            {
                this.bezier.last_segment = new BezierSegment(
                    this.bezier.last_segment.start,
                    this.tan_out,
                    pos,
                    pos
                );
            }
        }
    }

    on_drag(ev)
    {
        let p = new Point(ev.pos);
        this.next_tan_out = p.copy();
        this.tan_in = this.point.mul(2).sub(p);
        // Update the last segment
        this.bezier.last_segment = new BezierSegment(
            this.bezier.last_segment.start,
            this.tan_out,
            this.tan_in,
            this.point
        );
    }

    on_drag_end(ev)
    {
        let p = new Point(ev.pos);
        if ( this.state == this.states.Close )
        {
            this.bezier.last_segment = new BezierSegment(
                this.bezier.last_segment.start,
                this.tan_out,
                this.tan_in,
                this.first_point
            );
            this.commit_shape(false);
        }
        else
        {
            this.point = p;
            this.tan_out = this.next_tan_out;
            if ( this.state != this.states.Open )
            {
                this.bezier.add_segment(this.tan_out, this.point, this.point);
            }
            else
            {
                this.state = this.states.Mid;
                this.bezier.last_segment = new BezierSegment(
                    this.first_point,
                    this.tan_out,
                    this.point,
                    this.point
                );
            }
        }
    }

    commit_shape(discard_last)
    {
        if ( this.bezier )
        {
            if ( discard_last )
                this.bezier.segments.pop();

            let cmd = new ShapeAddCommand(
                "bezier",
                {
                    bezier: this.bezier,
                    ...this.editor.current_style,
                }
            );

            this.command_stack.push(cmd);
            this.bezier = null;
            this.editor.select_shape(cmd.data.id);
        }
    }

    on_deactivate()
    {
        this.commit_shape(true);
    }

    draw_foreground(context)
    {
        if ( this.bezier )
        {
            if ( this.state != this.states.Open )
            {
                context.fillStyle = this.editor.current_style.fill;
                context.strokeStyle = this.editor.current_style.stroke;
                context.lineWidth = this.editor.current_style.stroke_width;

                context.beginPath();
                this.bezier.draw_path(context);
                context.fill("evenodd");
                context.stroke();
            }

            if ( this.dragging )
            {
                context.strokeStyle = "silver";
                context.lineWidth = 1;
                context.beginPath();
                if ( this.state != this.states.Open )
                    context.moveTo(this.tan_in.x, this.tan_in.y);
                else
                    context.moveTo(this.first_point.x, this.first_point.y);
                context.lineTo(this.next_tan_out.x, this.next_tan_out.y);
                context.stroke();
            }

            this.handle.draw(context);
        }
    }

    on_install(editor)
    {
        editor.shape_types[this.slug] = BezierShape;
    }
}


export class FreehandTool extends DragTool
{
    constructor(command_stack)
    {
        super("freehand", "Freehand", command_stack);

        this.points = [];
        this.handle = new EditHandle(null, null, true, true);
    }

    on_drag_start(ev)
    {
        this.points = [new Point(this.drag_start)];
        this.handle.x = this.drag_start.x;
        this.handle.y = this.drag_start.y;
        this.handle.dragged = true;
    }

    on_drag(ev)
    {
        let pos = new Point(ev.pos);
        this.points.push(pos);
        this.handle.dragged = this.handle.under(pos);
    }

    on_drag_end(ev)
    {
        this.commit_shape(this.handle.dragged);
    }

    commit_shape(close)
    {
        if ( this.points.length )
        {
            if ( close )
                this.points.push(this.points[0]);
            let bez = simplify(this.points, 128);

            let cmd = new ShapeAddCommand(
                "bezier",
                {
                    bezier: bez,
                    ...this.editor.current_style,
                }
            );

            this.command_stack.push(cmd);
            this.points = [];
            this.editor.select_shape(cmd.data.id);
        }
    }

    on_deactivate()
    {
        this.commit_shape(false);
    }

    draw_foreground(context)
    {
        if ( this.points.length )
        {
            context.fillStyle = this.editor.current_style.fill;
            context.strokeStyle = this.editor.current_style.stroke;
            context.lineWidth = this.editor.current_style.stroke_width;

            context.beginPath();
            context.moveTo(this.points[0].x, this.points[0].y);
            for ( let i = 1; i < this.points.length; i++ )
                context.lineTo(this.points[i].x, this.points[i].y);
            context.fill("evenodd");
            context.stroke();
            this.handle.draw(context);
        }
    }
}


function triangle_area(points, index)
{
    let prev = points[index-1];
    let here = points[index];
    let next = points[index+1];

    return Math.abs(
        prev.x * here.y - here.x * prev.y +
        here.x * next.y - next.x * here.y +
        next.x * prev.y - prev.x * next.y
    );
}


function simplify(points, threshold)
{
    if ( points.length < 3 || threshold <= 0 )
        return make_bezier(points);

    // Algorithm based on https://bost.ocks.org/mike/simplify/
    let tris = [];

    tris.push(threshold); // [0] not used but keeping it for my own sanity
    for ( let i = 1; i < points.length - 1; i++ )
        tris.push(triangle_area(points, i));

    while ( tris.length )
    {
        let min = threshold;
        let index = -1;

        for ( let i = 0; i < tris.length; i++ )
        {
            if ( tris[i] < min )
            {
                index = i;
                min = tris[i];
            }
        }

        if ( index == -1 )
            break;

        tris.splice(index, 1);
        points.splice(index, 1);

        if ( index < tris.length )
            tris[index] = triangle_area(points, index);
        if ( index > 1 )
            tris[index-1] = triangle_area(points, index - 1);
    }

    return make_smooth_bezier(points);
}

function make_bezier(points)
{
    let bez = new Bezier();
    for ( let i = 1; i < points.length; i++ )
        bez.add_segment(points[i-1], points[i-1], points[i], points[i]);
    return bez;
}

function make_smooth_bezier(points)
{
    if ( points.length < 2 )
        return make_bezier(points);

    // rhs vector
    let a = [];
    let b = [];
    let c = [];
    let r = [];

    // left most segment
    a.push(0);
    b.push(2);
    c.push(1);
    r.push(points[0].add(points[1].mul(2)));

    // internal segments
    for ( let i = 1; i < points.length - 1; i++ )
    {
        a.push(1);
        b.push(4);
        c.push(1);
        r.push(points[i].mul(4).add(points[i+1].mul(2)));
    }

    // right segment
    a.push(2);
    b.push(7);
    c.push(0);
    r.push(points[points.length-2].mul(8).add(points[points.length-1]));

    // solves Ax=b with the Thomas algorithm (from Wikipedia)
    for ( let i = 1; i < points.length; i++ )
    {
        let m = a[i] / b[i-1];
        b[i] = b[i] - m * c[i - 1];
        r[i] = r[i].sub(r[i-1].mul(m));
    }

    let tan_in = [];
    let tan_out = [];
    let last = r[points.length-1].div(b[points.length-1]);
    tan_in[points.length-2] = last;
    tan_in[points.length-1] = points[points.length-1];
    tan_out[points.length-1] = points[points.length-1];

    for ( let i = points.length - 2; i >= 0; --i )
    {
        last = (r[i].sub(last.mul(c[i])).div(b[i]));
        let relative = (last.sub(points[i]));
        tan_in[i] = points[i].sub(relative);
        tan_out[i] = points[i].add(relative);
    }

    console.log(points, tan_in, tan_out);
    let bez = new Bezier();

    for ( let i = 1; i < points.length; i++ )
        bez.add_segment(points[i-1], tan_out[i-1], tan_in[i], points[i]);

    return bez;

}
