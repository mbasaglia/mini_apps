/**
 * \brief Wrapper around web sockets that dispatches events
 */
export class SocketConnection extends EventTarget
{
    constructor()
    {
        super();

        this.connected = false;
        this.reconnect = true;
        this.url = null;
        this.socket = null;
    }

    /**
     * \brief Connects to the given websocket url
     */
    connect(url)
    {
        if ( !this.reconnect )
            return;

        console.log(`Connecting to ${url}`);
        this.connected = true;
        this.url = url;
        this.socket = new WebSocket(url);
        this.socket.addEventListener("message", this.on_message_event.bind(this));
        this.socket.addEventListener("close", this._recover_socket.bind(this));
    }

    /**
     * \brief Dispatches a custom event on socket messages
     */
    on_message_event(ev)
    {
        const data = JSON.parse(ev.data);
        console.log("Message", data);
        this.dispatchEvent(new CustomEvent(data.type, {detail: data}));
    }

    /**
     * \brief Connects based on a settings file
     */
    connect_from_settings()
    {
        fetch("/settings.json")
        .then(resp => resp.json())
        .then((data => this.connect(data.socket)).bind(this));
    }

    /**
     * \brief Sends the given data through the socket
     */
    send(data)
    {
        this.socket.send(JSON.stringify(data));
    }

    /**
     * \brief Tries to reconnect the socket on disconnection
     */
    _recover_socket()
    {
        this.socket.close();
        console.error("Disconnected!");
        setTimeout(this.connect.bind(this), 1000, this.url);
    }
}

