import { App } from "../src/app.js";
import { Editor } from "./editor.js";
import { Playback } from "./playback.js";


export class GlaximiniApp extends App
{
    constructor(telegram)
    {
        super("glaximini", telegram);
        this.connection.addEventListener("sticker-id", this.send_sticker_ask.bind(this));

        this.canvas = document.getElementById("canvas");
        this.editor = new Editor(this.connection, this.canvas);
        this.editor.addEventListener("selected", this.update_style_inputs.bind(this));
        this.playback = new Playback(this.on_enter_frame.bind(this));
        this.playback.set_range(0, 180);

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

    /**
     * \brief Adds event listeners to the buttons and such
     */
    connect_ui()
    {
        document.getElementById("action-undo").addEventListener("click", this.undo.bind(this));
        document.getElementById("action-redo").addEventListener("click", this.redo.bind(this));
        document.getElementById("action-keyframe").addEventListener("click", this.add_keyframe.bind(this));
        document.getElementById("action-play").addEventListener("click", this.playback.start.bind(this.playback));
        document.getElementById("action-pause").addEventListener("click", this.playback.stop.bind(this.playback));
        document.getElementById("action-telegram").addEventListener("click", this.send_sticker_prepare.bind(this));

        this.inputs = {
            frame_slider: document.getElementById("frame"),
            frame_edit: document.getElementById("frame-edit"),
            fill: document.getElementById("action-fill"),
            stroke: document.getElementById("action-stroke"),
        };

        this.inputs.frame_slider.addEventListener("input", ((ev) => {
            this.playback.go_to(Number(ev.target.value));
        }).bind(this));

        for ( let tool of Object.values(this.editor.tools) )
        {
            let button = document.getElementById("tool-" + tool.slug);
            button.setAttribute("title", tool.name);
            button.addEventListener("click", (() => {
                this.switch_tool(tool);
            }).bind(this));
            tool._button = button;
        }

        const style_callback = ((ev) => this.on_style_control_input(ev.target)).bind(this);
        this.inputs.fill.addEventListener("input", style_callback);
        this.inputs.stroke.addEventListener("input", style_callback);
        this.update_style_inputs();
    }

    /**
     * \brief Switch the editor tool based on UI buttons
     */
    switch_tool(tool)
    {
        for ( let other_tool of Object.values(this.editor.tools) )
            other_tool._button.classList.remove("active");
        tool._button.classList.add("active");
        this.editor.switch_tool(tool.slug);
    }

    /**
     * \brief Updates fill/stroke inputs based on the selected shape
     */
    update_style_inputs()
    {
        this.inputs.fill.value = this.editor.current_style.fill.substr(0, 7);
        // this.inputs.fill_opacity.value = Number("0x" + this.editor.current_style.fill.substr(-2));
        this.inputs.stroke.value = this.editor.current_style.stroke.substr(0, 7);
        // this.inputs.stroke_opacity.value = Number("0x" + this.editor.current_style.stroke.substr(-2));
        // this.inputs.stroke_width.value = this.editor.current_style.stroke_width;
    }

    /**
     * \brief Apply fill/stroke changes on user input
     */
    on_style_control_input(input)
    {
        let new_style = {
            fill: this.inputs.fill.value + "ff",
            stroke: this.inputs.stroke.value + "ff",
            stroke_width: 4,
        };

        this.editor.current_style = new_style;
        if ( this.editor.current_shape )
        {
            let last = this.editor.stack.last();
            let shapes = this.editor.current_shape.styled_objects();
            let command = this.editor.stack.edit_command(shapes, new_style, false);
            command._input = input.id;
            if ( !last || last._input != command._input )
                this.editor.stack.commit();
        }

        this.editor.draw();
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

    to_lottie()
    {
        return this.editor.to_lottie(this.playback.min, this.playback.max, this.playback.fps);
    }

    send_sticker_prepare()
    {
        this.connection.send({type: "sticker", lottie: this.to_lottie()});
    }

    send_sticker_ask(ev)
    {
        this.webapp.switchInlineQuery(ev.detail.id, ["users", "groups", "channels", "bots"]);
    }
}
