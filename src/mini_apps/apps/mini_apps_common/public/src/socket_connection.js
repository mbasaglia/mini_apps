/**
 * \brief Wrapper around web sockets that dispatches events
 */
export class SocketConnection extends EventTarget
{
    /**
     * \brief Constructor
     */
    constructor(app_id)
    {
        super();

        this.connected = false;
        this.reconnect = true;
        this.url = null;
        this.socket = null;
        this.app_id = app_id;
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
     * \brief Sends the given data through the socket
     */
    send(data)
    {
        /// \todo if this.reconnect queue messages?
        if ( !this.connected )
            return;

        data.app = this.app_id;
        this.socket.send(JSON.stringify(data));
    }

    /**
     * \brief Tries to reconnect the socket on disconnection
     */
    _recover_socket()
    {
        this.socket.close();
        console.error("Disconnected!");
        this.dispatchEvent(new CustomEvent("socket.disconnected", {}));
        setTimeout(this.connect.bind(this), 1000, this.url);
    }
}

