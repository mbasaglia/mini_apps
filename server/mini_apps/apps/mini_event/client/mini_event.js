import { App } from "/mini_apps/src/app.js";


export class MiniEventApp extends App
{
    constructor(telegram, event_list_element)
    {
        super("mini_event", telegram);
        this.event_list_element = event_list_element;
        this.connection.addEventListener("event", this._on_event.bind(this));
        this.connection.addEventListener("delete-event", this._on_delete_event.bind(this));
        this.connection.addEventListener("events-loaded", this._on_events_loaded.bind(this));
        this.admin_visible = false;
        this.just_started = true
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

        document.getElementById("placeholder").style.display = "none";
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

        // Button to share an event within telegram using inline mode
        let button_share = button_row.appendChild(document.createElement("button"));
        button_share.innerText = "Share";
        button_share.addEventListener("click", () => {
            this.webapp.switchInlineQuery(`event:${ev.detail.id}`, ["users", "groups", "channels"])
        });

        // Button to toggle whether the user is attending an event
        let button_attend = button_row.appendChild(document.createElement("button"));
        if ( ev.detail.attending )
        {
            button_attend.innerText = "Leave Event";
            button_attend.addEventListener("click", () => {
                this.connection.send({
                    type: "leave",
                    event: ev.detail.id,
                });
            });
        }
        else
        {
            button_attend.innerText = "Attend";
            button_attend.addEventListener("click", () => {
                // We ask for permission to send messages to the user
                this.webapp.requestWriteAccess((confirm) => {
                    // If we can we register attendance
                    if ( confirm )
                    {
                        this.connection.send({
                            type: "attend",
                            event: ev.detail.id,
                        });
                    }
                    else
                    {
                        this.webapp.showAlert("To get event notifications you need to allow the bot to send you messages!");
                    }
                });
            });
        }

        // Admin-only button to delete the event
        if ( this.user.is_admin )
        {
            let button_delete = button_row.appendChild(document.createElement("button"));
            button_delete.classList.add("admin-action");
            button_delete.innerText = "Delete Event";
            button_delete.addEventListener("click", () => {
                // Show telegram native confirmation dialog, and delete if confirmed
                this.webapp.showConfirm(`Delete ${ev.detail.title}?`, (confirm) => {
                    if ( confirm )
                    {
                        this.connection.send({
                            type: "delete-event",
                            id: ev.detail.id,
                        });
                    }
                });
            });

            if ( this.admin_visible )
                button_delete.style.display = "block";
        }
    }

    /**
     * \brief Updates the DOM when an event is deleted on the server
     */
    _on_delete_event(ev)
    {
        let container = document.querySelector(`[data-event="${ev.detail.id}"]`);
        if ( container )
            container.parentNode.removeChild(container);
    }

    /**
     * \brief Called when the server has sent all the initial events after login
     */
    _on_events_loaded(ev)
    {
        // Only scroll on first start (not on server reconnection)
        if ( this.just_started )
        {
            let container = document.querySelector(`[data-event="${ev.detail.selected}"]`);
            if ( container )
                container.scrollIntoView(true);
        }

        this.just_started = false;
    }

    /**
     * \brief Sets up event listeners for UI elements (mostly the admin interface)
     */
    connect_ui()
    {
        const create_event_button = document.getElementById("create-event-button");
        const admin_buttons = document.getElementById("admin-buttons");
        const new_event_form = document.getElementById("new-event");
        const cancel_button = document.getElementById("cancel-button");
        const image_error = document.getElementById("image-error");

        // time input is very janky on tdesktop so we fall back
        if ( this.webapp.platform == "tdesktop" )
        {
            const time_input = document.getElementById("new-event-start");
            time_input.type = "text";
            time_input.placeholder = "12:00";
        }

        function toggle_add_event(show)
        {
            admin_buttons.style.display = show ? "none" : "flex";
            new_event_form.style.display = show ? "flex" : "none";
            new_event_form.reset();
            image_error.style.display = "none";
        }

        create_event_button.addEventListener("click", function(){
            toggle_add_event(true);
        });
        cancel_button.addEventListener("click", function(){
            toggle_add_event(false);
        });
        let events_app = this;
        new_event_form.addEventListener("submit", function(ev){
            ev.preventDefault();

            const data = new FormData(new_event_form);
            let entries = {};
            for ( let [name, value] of data.entries() )
                entries[name] = value;

            const reader = new FileReader();

            reader.onload = function(ev2)
            {
                if ( ev2.target.result > 512 * 1024 )
                {
                    image_error.style.display = "block";
                    image_error.innerText = "Image is too large, it should be less than 512KB";
                    return;
                }

                entries.image = {
                    name: entries.image.name,
                    base64: btoa(ev2.target.result),
                };
                toggle_add_event(false);
                events_app.connection.send({
                    type: "create-event",
                    ...entries
                });
            };

            reader.readAsBinaryString(entries["image"]);
        });

        const show_admin = document.getElementById("show-admin-button");
        const hide_admin = document.getElementById("hide-admin-button");
        show_admin.addEventListener("click", (function() {
            this.admin_visible = true;
            hide_admin.style.display = "block";
            show_admin.style.display = "none";
            for ( let element of document.querySelectorAll(".admin-action") )
                element.style.display = "block";
        }).bind(this));
        hide_admin.addEventListener("click", (function() {
            this.admin_visible = false;
            hide_admin.style.display = "none";
            show_admin.style.display = "block";
            for ( let element of document.querySelectorAll(".admin-action") )
                element.style.display = "none";
        }).bind(this));
    }
}
