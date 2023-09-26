import { CommandStack, KeyframeAddCommand, EventDestroyer } from "./command.js"
import { GroupObject, Layer } from "./shapes.js"
import { EllipseTool, RectangleTool, BezierTool } from "./tools.js"
import { SelectTool } from "./select_tool.js"
import { Matrix, Point } from "./math.js"



export class Editor extends EventTarget
{
    constructor(connection, canvas)
    {
        super();
        this.next_id = 0;
        this.canvas = canvas;
        this.context = canvas.getContext("2d");
        this.objects = {};
        this.root = new Layer("", this);
        this.current_layer = this.root;
        this.current_shape = null;
        this.current_style = {
            fill: "#cc88ffff",
            stroke: "#aa66ddff",
            stroke_width: 4,
        };
        this.shape_types = {
            "group": GroupObject,
        };
        this.initial_scale = 1;
        this.id_prefix = "id"

        this.stack = new CommandStack(this, connection);
        this.tools = {};
        this.tool = null;

        this.middle_drag = false;
        this.transform = new Matrix();
        this.inverse_transform = new Matrix();
        this.ev = new EventDestroyer();
        this.loading = true;

        for ( let tool of [SelectTool, EllipseTool, RectangleTool, BezierTool] )
            (new tool(this.stack)).install(this);

        for ( let ev of [
            "mouse_down", "mouse_move", "mouse_up", "wheel", "mouse_leave",
            "touch_start", "touch_move", "touch_end"
        ] )
            this.ev.add(canvas, ev.replace("_", ""), this["on_" + ev].bind(this));

        this.ev.add(connection, "document.edit", this.on_edit.bind(this));
        this.ev.add(connection, "document.loaded", this.on_load_finish.bind(this));
    }

    add_event(target, name, func)
    {
        this.events.push([target, name, func]);
        target.addEventListener(name, func);
    }

    destroy()
    {
        // Clear references in the hope the browser will delete them...

        // Clear Back references
        for ( let obj of Object.values(this.objects) )
            obj.editor = null;

        this.stack.editor = null;

        // Since our hopes are vain, remove all event listeners
        this.ev.destroy();
        this.stack.ev.destroy();

        // Clear references to children
        this.objects = null;
        this.root = null;
        this.stack = null;
        this.events = null;
    }

    select_shape(shape)
    {
        if ( typeof shape == "string" )
            shape = this.get_object(shape);

        this.current_shape = shape;
        if ( shape )
        {
            let style = shape.get_style();
            if ( style )
            {
                for ( let attr of ["fill", "stroke", "stroke_width"] )
                    this.current_style[attr] = style[attr];
            }
        }

        this.tool.on_selected(shape);

        this.dispatchEvent(new CustomEvent("selected", {detail: {shape: shape}}));
    }

    add_object(obj)
    {
        this.objects[obj.id] = obj;
    }

    generate_id()
    {
        let id = this.id_prefix + '-' + this.next_id;
        this.next_id += 1;
        return id;
    }

    object_from_command(data, cls)
    {
        if ( !data.id )
            data.id = this.generate_id();

        if ( data.id in this.objects )
            return this.objects[data.id];

        let obj = new cls(data.id, this);
        this.current_layer.insert_child(obj)
        this.add_object(obj);
        obj.assign_props(data.props);
        return obj;
    }

    shape_from_command(data)
    {
        return this.object_from_command(data, this.shape_types[data.shape]);
    }

    get_object(id)
    {
        return this.objects[id];
    }

    update_object(id, props)
    {
        this.objects[id].assign_props(props);
    }

    draw()
    {
        if ( this.loading )
            return;

        this.context.setTransform(1, 0, 0, 1, 0, 0);
        this.context.fillStyle = "silver";
        this.context.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.context.setTransform(...this.transform.to_canvas());
        this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.root.paint(this.context);

        this.tool.draw_foreground(this.context);
    }

    mouse_event_pos_untransformed(ev)
    {
        let rect = this.canvas.getBoundingClientRect();
        let pad = 0;

        if ( ev.touches )
        {
            if ( ev.touches.length )
            {
                ev = ev.touches[0];
                this.last_touch = ev;
            }
            else
            {
                ev = this.last_touch;
            }
        }

        let scale_x = this.canvas.width / this.canvas.clientWidth;
        let scale_y = this.canvas.width / this.canvas.clientWidth;

        return new Point(
            Math.max(pad, Math.min(this.canvas.clientWidth - pad, ev.clientX - rect.left)) * scale_x,
            Math.max(pad, Math.min(this.canvas.clientHeight - pad, ev.clientY - rect.top)) * scale_y,
        );
    }

    mouse_event_pos(ev)
    {
        let pos = this.mouse_event_pos_untransformed(ev);
        return new Point(this.inverse_transform.map(pos.x, pos.y));
    }

    switch_tool(slug)
    {
        this.tool.on_deactivate();
        this.tool = this.tools[slug];
        this.tool.on_activate();
        this.draw();
    }

    on_mouse_leave()
    {

    }

    on_touch_start(ev)
    {
        ev.preventDefault();

        if ( this.tool )
            this.tool.on_mouse_down(ev);

        this.draw();
    }

    on_touch_move(ev)
    {
        ev.preventDefault();

        if ( this.tool )
            this.tool.on_mouse_move(ev);

        this.draw();
    }

    on_touch_end(ev)
    {
        ev.preventDefault();

        if ( this.tool )
            this.tool.on_mouse_up(ev);

        this.draw();
    }

    on_mouse_down(ev)
    {
        ev.preventDefault();

        if ( ev.button == 1 )
        {
            this.drag_x = ev.clientX;
            this.drag_y = ev.clientY;
            this.middle_drag = true;
            return;
        }

        if ( this.tool )
            this.tool.on_mouse_down(ev);

        this.draw();
    }

    on_mouse_move(ev)
    {
        ev.preventDefault();

        let data = this.mouse_event_pos(ev);

        if ( this.middle_drag )
        {
            this.transform.translate(ev.clientX - this.drag_x, ev.clientY - this.drag_y);
            this.refresh_transform();
            this.drag_x = ev.clientX;
            this.drag_y = ev.clientY;
        }
        else if ( this.tool )
        {
            this.tool.on_mouse_move(ev);
        }

        this.draw();
    }

    on_mouse_up(ev)
    {
        ev.preventDefault();

        if ( ev.button == 1 )
            this.middle_drag = false;
        else if ( this.tool )
            this.tool.on_mouse_up(ev);

        this.draw();
    }

    on_edit(ev)
    {
        this.tool.on_edit();
        this.draw();
    }

    enter_frame(frame)
    {
        this.root.enter_frame(frame);
        this.tool.on_enter_frame(frame);
        this.draw();
    }

    add_keyframe()
    {
        if ( this.current_shape )
        {
            this.stack.push(new KeyframeAddCommand(
                this.current_shape.id,
                Math.round(this.current_shape.frame),
                this.current_shape.props
            ));
        }
    }

    on_wheel(ev)
    {
        let center = this.mouse_event_pos_untransformed(ev);
        this.zoom(center, ev.deltaY);
    }

    reset_view()
    {
        this.transform = new Matrix();
        this.transform.scale(this.initial_scale, this.initial_scale);
        this.refresh_transform();
        this.dispatchEvent(new CustomEvent("zoomed", {detail: {zoom: 1}}));
        this.draw();
    }

    zoom(center, direction)
    {
        this.transform.translate(-center.x, -center.y);

        if ( direction < 0 )
            this.transform.scale(0.8, 0.8);
        else if ( direction > 0 )
            this.transform.scale(1.25, 1.25);

        this.transform.translate(center.x, center.y);
        this.refresh_transform();
        this.draw();

        this.dispatchEvent(new CustomEvent("zoomed", {detail: {zoom: this.transform.elements[0]}}));
    }

    refresh_transform()
    {
        this.inverse_transform = this.transform.inverted();
    }

    set_parent(child_id, parent_id)
    {
        let child = this.get_object(child_id);
        if ( child.parent )
            child.parent.remove_child(child);

        let parent = parent_id != null ? this.get_object(parent_id) : this.root;
        parent.insert_child(child);
    }

    on_load_finish()
    {
        this.root.enter_frame(this.root.frame);
        this.loading = false;
        this.draw();
    }

    set_initial_scale(scale)
    {
        this.initial_scale = scale;
        this.transform.scale(scale, scale);
        this.refresh_transform();
        this.dispatchEvent(new CustomEvent("zoomed", {detail: {zoom: scale}}));
    }
}
