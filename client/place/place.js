import { App } from "../src/app.js";
import { rgb_to_hex } from "../glaximini/color.js";


export class Place extends App
{
    constructor(telegram)
    {
        super("place", telegram);
        this.pixels = [];
        this.palette = [];
        this.current_color = 0;
        this.wait_time = 60;
        this.current_color_element = null;
        this.when = document.getElementById("when");
        this.connection.addEventListener("setup", this.on_setup.bind(this));
        this.connection.addEventListener("refresh", this.on_refresh.bind(this));
        this.connection.addEventListener("delay", this.on_delay.bind(this));
        window.setInterval(this.on_count_down.bind(this), 1000);
    }

    on_setup(ev)
    {
        let parent = document.getElementById("place");
        parent.innerHTML = "";
        this.pixels = [];

        for ( let y = 0; y < ev.detail.height; y++ )
        {
            let row = parent.appendChild(document.createElement("div"));
            row.classList.add("row");

            for ( let x = 0; x < ev.detail.height; x++ )
            {
                let pixel = row.appendChild(document.createElement("div"));
                pixel.classList.add("pixel");
                pixel.addEventListener("click", (() => this.on_click(x, y)).bind(this));
                this.pixels.push(pixel);
            }
        }

        let palette_parent = document.getElementById("palette");
        palette_parent.innerHTML = "";

        this.palette = [];
        for ( let i = 0; i < ev.detail.palette.length; i++ )
        {
            let color = rgb_to_hex(this.palette[i])
            this.palette.push(color);

            let button = parent.appendChild(document.createElement("div"));
            if ( i == 0 )
            {
                this.current_color_element = button;
                button.classList.add("active");
            }

            button.style.background = color;
            button.addEventListener("click", (() => {
                this.current_color_element.classList.remove("active");
                this.current_color_element = button;
                this.current_color_element.classList.add("active");
                this.current_color = i;
            }).bind(this));
        }
    }

    on_click(x, y)
    {
        if ( this.wait_time <= 0 )
            this.connection.send({type: "pixel", x: x, y: y, color: this.current_color});
    }

    on_delay(ev)
    {
        this.wait_time = ev.detail.delay + 0.5;
    }

    on_count_down()
    {
        if ( this.wait_time > 0 )
        {
            this.wait_time -= 1;
            if ( this.wait_time > 0 )
            {
                let seconds = Math.round(this.wait_time);
                this.when.innerText = `in ${seconds} seconds`;
                return;
            }
        }

        this.when.innerText ="right now!";
    }

    on_refresh(ev)
    {
        for ( let i = 0; i < ev.detail.hash.length; i++ )
        {
            let color_index = ev.detail.hash.charCodeAt(i);
            let color = this.palette[color_index];
            this.pixels[i].style.background = color;
        }
    }
}
