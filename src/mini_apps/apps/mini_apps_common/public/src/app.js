import { SocketConnection } from "./socket_connection.js";

/**
 * \brief Class that manages the socket connection and telegram authentication
 */
export class App
{
    /**
     * \brief Constructor
     */
    constructor(app_id, telegram)
    {
        this.webapp = telegram.WebApp;

        this.user = {};

        this.connection = new SocketConnection(app_id);
        this.connection.addEventListener("connect", this._on_connect.bind(this));
        this.connection.addEventListener("disconnect", this._on_disconnect.bind(this));
        this.connection.addEventListener("welcome", this._on_welcome.bind(this));
    }

    /**
     * \brief Sends the log in message with the mini app init data
     */
    log_in(telegram_data)
    {
        this.connection.send({
            type: "login",
            data: telegram_data.initData
        });
    }

    /**
     * \brief When receiving a disconnect message, stops trying to reconnect
     */
    _on_disconnect(ev)
    {
        this.connection.reconnect = false;
    }

    /**
     * \brief Called then the server acknowledges the connection
     */
    _on_connect(ev)
    {
        this.log_in(this.webapp);
    }

    /**
     * \brief Called when the server sends user details
     */
    _on_welcome(ev)
    {
        this.user = ev.detail;
    }

    connect(url)
    {
        this.connection.connect(url);
    }
}
