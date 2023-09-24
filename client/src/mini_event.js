import { App } from "./app.js";


export class MiniEventApp extends App
{
    constructor(telegram, event_list_element)
    {
        super(telegram);
        this.event_list_element = event_list_element;
        this.connection.addEventListener("event", this._on_event.bind(this));
    }

    /**
     * \brief Updates the DOM when an event is added / modified on the server
     */
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

        row = info.appendChild(document.createElement("tr"));
        row.appendChild(document.createElement("th")).appendChild(
            document.createTextNode("Attendees")
        );
        row.appendChild(document.createElement("td")).appendChild(
            document.createTextNode(ev.detail.attendees)
        );

        let button_row = div.appendChild(document.createElement("p"));
        let button_attend = button_row.appendChild(document.createElement("button"));

        if ( ev.detail.attending )
        {
            button_attend.appendChild(document.createTextNode("Leave Event"));
            button_attend.addEventListener("click", () => {
                this.connection.send({
                    type: "leave",
                    event: ev.detail.id,
                });
            });
        }
        else
        {
            button_attend.appendChild(document.createTextNode("Attend"));
            button_attend.addEventListener("click", () => {
                this.connection.send({
                    type: "attend",
                    event: ev.detail.id,
                });
            });
        }
    }
}
