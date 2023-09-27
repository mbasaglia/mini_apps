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
