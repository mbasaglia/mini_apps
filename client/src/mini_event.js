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
     * \brief Called when the server sends user details
     */
    _on_welcome(ev)
    {
        super._on_welcome(ev);

        // Toggle admin widget based on the user we got from the server
        document.getElementById("admin-actions").style.display = (
            this.user.is_admin ? "block" : "none"
        );
    }

    /**
     * \brief Updates the DOM when an event is added / modified on the server
     */
    _on_event(ev)
    {
        let container = document.querySelector(`[data-event="${ev.detail.id}"]`);
        let title;
        let preview_image;
        let description;
        let start;
        let duration;
        let attendees;
        let button_row;

        if ( container )
        {
            // Find the right elements
            title = container.querySelector("header");
            preview_image = container.querySelector("img");
            description = container.querySelector(".description");
            let table_cells = container.querySelectorAll("td");
            start = table_cells[0];
            duration = table_cells[1];
            attendees = table_cells[2];
            button_row = container.querySelector(".buttons");
            button_row.innerHTML = "";
        }
        else
        {
            // Create the structure
            container = this.event_list_element.appendChild(document.createElement("article"));
            container.dataset.event = ev.detail.id;
            container.classList.add("event");
            title = container.appendChild(document.createElement("header"));

            let content = container.appendChild(document.createElement("section"));
            preview_image = content.appendChild(document.createElement("img"));

            description = content.appendChild(document.createElement("p"));
            description.classList.add("description");

            let info = content.appendChild(document.createElement("table"));
            let row = info.appendChild(document.createElement("tr"));
            row.appendChild(document.createElement("th")).appendChild(
                document.createTextNode("Starts at")
            );
            start = row.appendChild(document.createElement("td"));

            row = info.appendChild(document.createElement("tr"));
            row.appendChild(document.createElement("th")).appendChild(
                document.createTextNode("Duration")
            );
            duration = row.appendChild(document.createElement("td"));

            row = info.appendChild(document.createElement("tr"));
            row.appendChild(document.createElement("th")).appendChild(
                document.createTextNode("Attendees")
            );
            attendees = row.appendChild(document.createElement("td"));

            button_row = container.appendChild(document.createElement("p"));
            button_row.classList.add("buttons");
        }

        // Set the text / content
        title.innerText = ev.detail.title;
        description.innerText = ev.detail.description;
        start.innerText = ev.detail.start;
        duration.innerText = ev.detail.duration + " hours";
        attendees.innerText = ev.detail.attendees;

        preview_image.setAttribute("src", ev.detail.image);
        preview_image.setAttribute("alt", ev.detail.title);

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
