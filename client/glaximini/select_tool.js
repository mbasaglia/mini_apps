import { EllipseShape, RectangleShape, BezierShape, GroupObject } from "./shapes.js"
import { EditHandle, DragTool } from "./tools.js"
import { Point } from "./math.js"
import { BezierSegment, Bezier } from "./bezier.js"


class HandleRectTop extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, true, false);
    }

    refresh_pos()
    {
        this.x = this.shape.props.left + this.shape.props.width / 2;
        this.y = this.shape.props.top;
    }

    on_drag(x, y)
    {
        if ( y > this.shape.props.top + this.shape.props.height )
            return null;

        return {
            top: y,
            height: this.shape.props.height - (y - this.shape.props.top),
        }
    }
}

class HandleRectLeft extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, true);
    }

    refresh_pos()
    {
        this.x = this.shape.props.left;
        this.y = this.shape.props.top + this.shape.props.height / 2;
    }

    on_drag(x, y)
    {
        if ( x > this.shape.props.left + this.shape.props.width )
            return null;

        return {
            left: x,
            width: this.shape.props.width - (x - this.shape.props.left),
        };
    }
}


class HandleRectRight extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, true);
    }

    refresh_pos()
    {
        this.x = this.shape.props.left + this.shape.props.width;
        this.y = this.shape.props.top + this.shape.props.height / 2;
    }

    on_drag(x, y)
    {
        if ( x < this.shape.props.left )
            return null;

        return {
            width: x - this.shape.props.left,
        };
    }
}


class HandleRectBottom extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, true, false);
    }

    refresh_pos()
    {
        this.x = this.shape.props.left + this.shape.props.width / 2;
        this.y = this.shape.props.top + this.shape.props.height;
    }

    on_drag(x, y)
    {
        if ( y < this.shape.props.top )
            return null;

        return {
            height: y - this.shape.props.top,
        };
    }
}

class HandleRectCenter extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
    }

    refresh_pos()
    {
        this.x = this.shape.props.left + this.shape.props.width / 2;
        this.y = this.shape.props.top + this.shape.props.height / 2;
    }

    on_drag(x, y)
    {
        return {
            left: x - this.shape.props.width / 2,
            top: y - this.shape.props.height / 2,
        };
    }
}


class HandleEllipseCenter extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
    }

    refresh_pos()
    {
        this.x = this.shape.props.cx;
        this.y = this.shape.props.cy;
    }

    on_drag(x, y)
    {
        return {
            cx: x,
            cy: y,
        };
    }
}


class HandleEllipseX extends EditHandle
{
    constructor(stack, shape, direction)
    {
        super(stack, shape, false, true);
        this.direction = direction;
    }

    refresh_pos()
    {
        this.x = this.shape.props.cx + this.direction * this.shape.props.rx;
        this.y = this.shape.props.cy;
    }

    on_drag(x, y)
    {
        return {
            rx: Math.abs(x - this.shape.props.cx),
        };
    }
}

class HandleEllipseY extends EditHandle
{
    constructor(stack, shape, direction)
    {
        super(stack, shape, true, false);
        this.direction = direction;
    }

    refresh_pos()
    {
        this.x = this.shape.props.cx;
        this.y = this.shape.props.cy + this.direction * this.shape.props.ry;
    }

    on_drag(x, y)
    {
        return {
            ry: Math.abs(y - this.shape.props.cy),
        };
    }
}


class HandleBezierPoint extends EditHandle
{
    constructor(stack, shape, first, last)
    {
        super(stack, shape, false, false);
        this.first = first;
        this.last = last;
    }

    bez_pos()
    {
        let p;

        if ( this.first != -1 )
            return this.shape.props.bezier.segments[this.first].start;
        else
            return this.shape.props.bezier.segments[this.last].end;
    }

    refresh_pos()
    {
        let p = this.bez_pos();
        this.x = p.x;
        this.y = p.y;
    }

    on_drag(x, y)
    {
        let p = new Point(x, y);
        let delta = p.sub(this.bez_pos());
        let bez = new Bezier(this.shape.props.bezier.segments.slice());
        if ( this.first != -1 )
        {
            bez.segments[this.first] = new BezierSegment(
                p,
                bez.segments[this.first].points[1].add(delta),
                bez.segments[this.first].points[2],
                bez.segments[this.first].points[3],
            );
        }
        if ( this.last != -1 )
        {
            bez.segments[this.last] = new BezierSegment(
                bez.segments[this.last].points[0],
                bez.segments[this.last].points[1],
                bez.segments[this.last].points[2].add(delta),
                p,
            );
        }

        return {
            bezier: bez
        };
    }
}


class HandleBezierTangent extends EditHandle
{
    constructor(stack, shape, segment, tangent, origin)
    {
        super(stack, shape, false, false, EditHandle.Shape.Diamond);
        this.segment = segment;
        this.tangent = tangent;
        this.origin = origin;
        this.colors = {
            Normal: "#A1ADB7",
            Highlight: "#D9E0E6",
            Drag: "#FFFFFF",
        };
    }

    refresh_pos()
    {
        let p = this.shape.props.bezier.segments[this.segment].points[this.tangent];
        this.x = p.x;
        this.y = p.y;
    }

    on_drag(x, y)
    {
        let bez = new Bezier(this.shape.props.bezier.segments.slice());
        let pts = bez.segments[this.segment].points.slice();
        pts[this.tangent] = new Point(x, y);
        bez.segments[this.segment] = new BezierSegment(...pts);

        return {
            bezier: bez
        };
    }

    draw(context, highlight)
    {
        if ( highlight && !this.dragged )
            context.strokeStyle = this.colors.Highlight;
        else
            context.strokeStyle = this.colors.Normal;

        context.lineWidth = 1;

        context.beginPath();
        let p1 = this.shape.props.bezier.segments[this.segment].points[this.origin];
        context.moveTo(p1.x, p1.y)
        let p2 = this.shape.props.bezier.segments[this.segment].points[this.tangent];
        context.lineTo(p2.x, p2.y)
        context.stroke();
        super.draw(context, highlight);
    }
}


class HandleBezierCenter extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
    }

    refresh_pos()
    {
        let c = this.shape.bounding_box().center;
        this.x = c.x;
        this.y = c.y;
    }

    on_drag(x, y)
    {
        let c = this.shape.bounding_box().center;
        let dx = x - c.x;
        let dy = y - c.y;
        return {
            bezier: this.shape.props.bezier.dragged(new Point(dx, dy))
        };
    }
}


class HandleGroupPosition extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
    }

    refresh_pos()
    {
        let c = this.shape.bounding_box().center;
        this.x = c.x;
        this.y = c.y;
    }

    on_drag(x, y)
    {
        let delta = new Point(x - this.x, y - this.y);
        return {
            position: this.shape.props.position.add(delta),
        };
    }
}

class HandleGroupAnchor extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
    }

    refresh_pos()
    {
        let c = this.shape.props.position;
        this.x = c.x;
        this.y = c.y;
    }

    on_drag(x, y)
    {
        let delta = new Point(x - this.x, y - this.y);
        return {
            position: this.shape.props.position.add(delta),
            anchor: this.shape.props.anchor.add(delta),
        };
    }
}

class HandleGroupRotation extends EditHandle
{
    constructor(stack, shape)
    {
        super(stack, shape, false, false);
        this.old_angle = 0;
    }

    refresh_pos()
    {
        let bb = this.shape.bounding_box();
        let corners = bb.corners;
        let top = corners[0].add(corners[1]).div(2);
        this.x = top.x;
        this.y = top.y;
        this.center = this.shape.props.position;
        this.old_angle = Math.atan2(this.y - this.center.y, this.x - this.center.x);
    }

    on_drag(x, y)
    {
        let angle = Math.atan2(y - this.center.y, x - this.center.x);
        let angle_delta = angle - this.old_angle;
        this.old_angle = angle;
        return {
            rotation: this.shape.props.rotation + angle_delta,
        };
    }
}

export class SelectTool extends DragTool
{
    constructor(command_stack)
    {
        super("select", "Select", command_stack);
        this.under_mouse = null;
        this.handles = [];
        this.active_handle = null;
        this.highlight_handle = null;
        this.active_object = null;
        this.position_handle = null;
    }

    prepare_handles()
    {
        this.handles = [];
        this.active_handle = null;
        this.active_object = this.editor.current_shape;
        this.position_handle = null;

        if ( this.editor.current_shape instanceof RectangleShape )
        {
            this.handles.push(new HandleRectLeft(this.command_stack, this.editor.current_shape));
            this.handles.push(new HandleRectTop(this.command_stack, this.editor.current_shape));
            this.handles.push(new HandleRectRight(this.command_stack, this.editor.current_shape));
            this.handles.push(new HandleRectBottom(this.command_stack, this.editor.current_shape));
            this.position_handle = new HandleRectCenter(this.command_stack, this.editor.current_shape);
            this.handles.push(this.position_handle);
        }
        else if ( this.editor.current_shape instanceof EllipseShape )
        {
            this.position_handle = new HandleEllipseCenter(this.command_stack, this.editor.current_shape);
            this.handles.push(this.position_handle);
            this.handles.push(new HandleEllipseX(this.command_stack, this.editor.current_shape, 1));
            this.handles.push(new HandleEllipseX(this.command_stack, this.editor.current_shape, -1));
            this.handles.push(new HandleEllipseY(this.command_stack, this.editor.current_shape, 1));
            this.handles.push(new HandleEllipseY(this.command_stack, this.editor.current_shape, -1));
        }
        else if ( this.editor.current_shape instanceof BezierShape )
        {
            let segs = this.editor.current_shape.props.bezier.segments;
            let closed = this.editor.current_shape.props.bezier.is_closed();
            let prev = closed ? segs.length - 1 : -1;
            let bottom = [];
            let top = [];
            for ( let i = 0; i < segs.length; i++ )
            {
                bottom.push(new HandleBezierTangent(this.command_stack, this.editor.current_shape, i, 1, 0));
                bottom.push(new HandleBezierTangent(this.command_stack, this.editor.current_shape, i, 2, 3));
                top.push(new HandleBezierPoint(this.command_stack, this.editor.current_shape, i, prev));
                prev = i;
            }
            if ( !closed )
                top.push(new HandleBezierPoint(this.command_stack, this.editor.current_shape, -1, segs.length-1));

            this.handles = bottom.concat(top);
            this.position_handle = new HandleBezierCenter(this.command_stack, this.editor.current_shape);
            this.handles.push(this.position_handle);
        }
        else if ( this.editor.current_shape instanceof GroupObject )
        {
            this.position_handle = new HandleGroupPosition(this.command_stack, this.editor.current_shape);
            this.handles.push(this.position_handle);
            this.handles.push(new HandleGroupRotation(this.command_stack, this.editor.current_shape));
            this.handles.push(new HandleGroupAnchor(this.command_stack, this.editor.current_shape));
        }

        this.refresh_handles();
    }

    on_drag_start(ev)
    {
        this.active_handle = null;
        for ( let i = this.handles.length - 1; i >= 0; i-- )
        {
            if ( this.handles[i].under(ev.pos) )
            {
                this.active_handle = this.handles[i];
                this.active_handle.drag_start();
                break;
            }
        }

        this.maybe_drag = false;
        if ( !this.active_handle )
        {
            this.dragging = false;
            this.under_mouse = this.command_stack.editor.root.object_at(ev.pos);
            this.maybe_drag = this.under_mouse != null;
            if ( this.under_mouse && this.under_mouse !== this.active_object )
            {
                this.editor.select_shape(this.under_mouse);
            }
        }
        else
        {
            this.under_mouse = null;
        }

        this.highlight_handle = null;
    }

    on_drag(ev)
    {
        if ( this.active_handle )
        {
            this.active_handle.drag(ev);
            this.refresh_handles();
        }
        else if ( this.maybe_drag )
        {
            this.maybe_drag = false;
            this.active_handle = this.position_handle;
            this.active_handle.drag_start(ev.pos);
        }
    }

    on_drag_end(ev)
    {
        if ( this.active_handle )
        {
            this.active_handle.drag_end();
            this.highlight_handle = this.active_handle;
            this.active_handle = null;
        }
    }

    on_mouse_move(ev)
    {
        if ( this.maybe_drag && this.position_handle )
            this.dragging = true;

        super.on_mouse_move(ev);
        if ( !this.active_handle )
        {
            let pos = this.editor.mouse_event_pos(ev);

            this.highlight_handle = null;
            for ( let handle of this.handles )
            {
                if ( handle.under(pos) )
                {
                    this.highlight_handle = handle;
                    break;
                }
            }

            this.under_mouse = this.command_stack.editor.root.object_at(pos);
        }
    }

    on_mouse_up(ev)
    {
        this.maybe_drag = false;
        if ( !this.dragging )
            this.editor.select_shape(this.under_mouse);
        super.on_mouse_up(ev);
    }

    on_selected(shape)
    {
        this.prepare_handles();
    }

    highlight(context, shape)
    {
        context.strokeStyle = EditHandle.Colors.Normal;
        context.lineWidth = 1;
        context.beginPath();
        let bb = shape.bounding_box(true);
        let corners = bb.corners;
        context.moveTo(corners[corners.length - 1].x, corners[corners.length - 1].y);
        for ( let corner of corners )
            context.lineTo(corner.x, corner.y);
        context.stroke();
    }

    draw_foreground(context)
    {
        if ( this.under_mouse )
            this.highlight(context, this.under_mouse);

        if ( this.editor.current_shape )
            this.highlight(context, this.editor.current_shape);

        for ( let handle of this.handles )
            handle.draw(context, handle === this.highlight_handle);
    }

    refresh_handles()
    {
        for ( let handle of this.handles )
            handle.refresh_pos();
    }

    on_activate()
    {
        if ( this.editor.current_shape )
            this.prepare_handles();
    }

    on_deactivate()
    {
        if ( this.active_handle )
            this.active_handle.drag_end();
        this.handles = [];
        this.active_handle = null;
        this.under_mouse = null;
    }

    on_edit()
    {
        this.refresh_handles()
    }

    on_enter_frame()
    {
        this.refresh_handles();
    }
}
