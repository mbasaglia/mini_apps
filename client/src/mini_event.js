import { SocketConnection } from "./socket_connection.js";

export class MiniEventApp
{
    constructor(telegram, event_list_element)
    {
        this.webapp = telegram.WebApp;

        this.event_list_element = event_list_element;

        this.connection = new SocketConnection();
        this.connection.addEventListener("connect", this._on_connect.bind(this));
        this.connection.addEventListener("disconnect", this._on_disconnect.bind(this));
        this.connection.addEventListener("event", this._on_event.bind(this));

        this.connection.connect_from_settings();
    }

    log_in(telegram_data)
    {
        this.connection.send({
            type: "login",
            data: telegram_data.initData
        });
    }

    _on_disconnect(ev)
    {
        this.connection.reconnect = false;
    }

    _on_connect(ev)
    {
        this.log_in(this.webapp);
    }

    _on_event(ev)
    {
        let div = document.querySelector(`[data-event="${ev.detail.id}"]`);
        if ( div )
        {
            div.innerHTML = "";
        }
        else
        {
            div = this.event_list_element.appendChild(document.createElement("article"));
            div.dataset.event = ev.detail.id;
        }

        div.classList.add("event");
        div.appendChild(document.createElement("header")).appendChild(
            document.createTextNode(ev.detail.title)
        );

        let content = div.appendChild(document.createElement("section"));


        let img = content.appendChild(document.createElement("img"));
        img.setAttribute("src", ev.detail.image);
        img.setAttribute("alt", ev.detail.title);

        content.appendChild(document.createElement("p")).appendChild(
            document.createTextNode(ev.detail.description)
        );

        let info = content.appendChild(document.createElement("table"));
        let row = info.appendChild(document.createElement("tr"));
        row.appendChild(document.createElement("th")).appendChild(
            document.createTextNode("Starts at")
        );
        row.appendChild(document.createElement("td")).appendChild(
            document.createTextNode(ev.detail.start)
        );
        row = info.appendChild(document.createElement("tr"));
        row.appendChild(document.createElement("th")).appendChild(
            document.createTextNode("Duration")
        );
        row.appendChild(document.createElement("td")).appendChild(
            document.createTextNode(ev.detail.duration + " hours")
        );

        let button_row = div.appendChild(document.createElement("p"));
        let button_attend = button_row.appendChild(document.createElement("button"));
        button_attend.appendChild(document.createTextNode("Attend"));
    }
}
