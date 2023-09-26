import { App } from "./src/app.js";
import { Editor } from "./editor.js";


class Playback
{
    constructor(callback)
    {
        this.callback = callback;
        this.run = false;
        this.frame = 0;
        this.min = 0;
        this.max = 0;
        this.duration = 180;
        this.fps = 60;
        this.request_id = null;
        this.start_frame = null;
        this.start_time = null;
    }

    _request_frame()
    {
        this.request_id = window.requestAnimationFrame(this._on_frame.bind(this));
    }

    set_range(min, max)
    {
        this.min = min;
        this.max = max;
        this.duration = max - min;
        this.frame = min;
        this.callback(this.frame);
    }

    start()
    {
        this.run = true;
        this.start_time = null;
        this.start_frame = this.frame;
        this._request_frame();
    }

    _on_frame(timer)
    {
        if ( this.start_time == null )
            this.start_time = timer;

        let delta_frames = this.start_frame + (timer - this.start_time) / 1000 * this.fps;
        this.frame = this.min + (delta_frames % this.duration);
        this.callback(this.frame);

        if ( this.run )
            this._request_frame();
    }

    stop()
    {
        this.run = false;
        if ( this.request_id !== null )
            window.cancelAnimationFrame(this.request_id);
    }

    go_to(frame)
    {
        this.frame = frame;
        this.callback(this.frame);
    }
}


export class GlaximiniApp extends App
{
    constructor(telegram)
    {
        super("glaximini", telegram);
        this.canvas = document.getElementById("canvas");
        this.editor = new Editor(this.connection, this.canvas);
        this.playback = new Playback(this.on_enter_frame.bind(this));

        // Debug mode when accessing from browser that disables server side stuff
        if ( !this.webapp.initData )
        {
            this.connection.reconnect = false;
            this.connection.socket = {
                send: console.log
            };
            this.editor.loading = false;
        }

        this.connect_ui();
    }


    /**
     * \brief Called when the server sends user details
     */
    _on_welcome(ev)
    {
        super._on_welcome(ev);
        this.editor.loading = false;
    }


    connect_ui()
    {
        document.getElementById("action-undo").addEventListener("click", this.undo.bind(this));
        document.getElementById("action-redo").addEventListener("click", this.redo.bind(this));
        document.getElementById("action-keyframe").addEventListener("click", this.add_keyframe.bind(this));
        document.getElementById("action-play").addEventListener("click", this.playback.start.bind(this.playback));
        document.getElementById("action-pause").addEventListener("click", this.playback.stop.bind(this.playback));

        this.inputs = {
            frame_slider: document.getElementById("frame"),
            frame_edit: document.getElementById("frame-edit"),
        };

        this.inputs.frame_slider.addEventListener("input", ((ev) => {
            this.playback.go_to(Number(ev.target.value));
        }).bind(this));

        for ( let tool of Object.values(this.editor.tools) )
        {
            let button = document.getElementById("tool-" + tool.slug);
            button.setAttribute("title", tool.name);
            button.addEventListener("click", (() => {
                this.editor.switch_tool(tool.slug);
            }).bind(this));
        }
    }

    undo()
    {
        this.editor.stack.undo();
    }

    redo()
    {
        this.editor.stack.redo();
    }

    on_enter_frame(frame)
    {
        if ( !this.editor )
            return;

        frame = Math.round(frame);
        if ( frame != Math.round(this.editor.root.frame) )
        {
            this.editor.enter_frame(frame);
            this.inputs.frame_slider.value = this.inputs.frame_edit.value = frame;
        }
    }

    add_keyframe()
    {
        this.editor.add_keyframe();
    }
}
