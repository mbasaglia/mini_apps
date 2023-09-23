import { SocketConnection } from "./socket_connection.js";

export class MiniEventApp
{
    constructor(telegram)
    {
        this.webapp = telegram.WebApp;
        this.connection = new SocketConnection();
        this.connection.addEventListener("connect", this._on_connect.bind(this));
        this.connection.connect_from_settings();
    }

    _on_connect(ev)
    {
        this.log_in(this.webapp);
    }

    log_in(telegram_data)
    {
        this.connection.send({
            type: "login",
            data: telegram_data.initData
        });
    }
}
