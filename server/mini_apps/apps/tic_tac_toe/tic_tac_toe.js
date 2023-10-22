import { App } from "/mini_apps/src/app.js";


export class TicTacToe extends App
{
    constructor(telegram)
    {
        super("tic_tac_toe", telegram);
        this.screen = "loading";
        this.screens = {};
        this.friend = null;
        this.player = {};
        this.game = null;
        this.game_id = null;

        for ( let screen of document.querySelectorAll(".screen") )
            this.screens[screen.id] = screen;

        for ( let button of document.querySelectorAll("button") )
        {
            button.addEventListener("click", this.button_click.bind(this));
        }

        this.elements = {
            request_error: document.getElementById("request-error"),
            request_input: document.getElementById("request-input"),
            request_name: document.getElementById("request-name"),
            opponent_name: document.getElementById("opponent-name"),
            opponent_text: document.getElementById("opponent-text"),
            button_restart: document.getElementById("button-restart"),
            turn: document.getElementById("turn"),
            cells: Array.from(document.querySelectorAll(".cell")),
            new_game_id: document.getElementById("new-game-id"),
            board: document.getElementById("board"),
        };

        for ( let cell of this.elements.cells )
        {
            cell.addEventListener("click", this.on_cell_clicked.bind(this));
        }

        let message_types = [
            "game.join",
            "game.created",
            "game.leave",
            "game.state",
            "join.sent",
            "join.fail",
            "join.request",
            "socket.disconnected",
        ]
        for ( let type of message_types )
            this.connection.addEventListener(type, this["on_" + type.replace(".", "_")].bind(this));
    }

    /**
     * \brief Called when the server sends user details
     */
    _on_welcome(ev)
    {
        super._on_welcome(ev);
        this.elements.request_error.style.display = "none";
        this.switch_screen("start");
        this.player.name = ev.detail.name;
    }

    /**
     * \brief Changes the current screen to the one indicated by \p name
     */
    switch_screen(name)
    {
        if ( name == this.screen )
            return;
        this.screens[this.screen].style.display = "none";
        this.screen = name;
        this.screens[this.screen].style.display = "block";
    }

    /**
     * \brief Event handler for button clicks
     */
    button_click(ev)
    {
        switch ( ev.target.id.replace("button-", "") )
        {
            case "create":
                this.connection.send({type: "game.new"});
                return;
            case "restart":
            case "cancel-new-game":
                this.connection.send({type: "game.leave"});
                this.switch_screen("start");
                return;
            case "send-request":
                let value = this.elements.request_input.value;
                if ( value === "" )
                {
                    this.elements.request_error.style.display = "block";
                    this.elements.request_error.innerText = "You must enter a code";
                }
                else
                {
                    this.connection.send({type: "game.join", game: value});
                    this.switch_screen("request-sent");
                }
                return;
            case "request-accept":
                if ( !this.friend )
                    return;
                this.connection.send({type: "join.accept", who: this.friend.id});
                this.switch_screen("loading");
                return;
            case "request-refuse":
                if ( !this.friend )
                    return;
                this.connection.send({type: "join.refuse", who: this.friend.id});
                this.switch_screen("new-game");
                return;
            case "copy-code":
                navigator.clipboard.writeText(this.elements.new_game_id.innerText);
                return;
            case "send-code":
                // Random query to ensure Telegram doesn't cache the result
                this.webapp.switchInlineQuery(String(this.game_id), ["users"]);
                return;
        }
    }

    /**
     * \brief Connection dropped, show loading screen
     */
    on_socket_disconnected(ev)
    {
        this.switch_screen("loading");
    }

    /**
     * \brief Joining a game, ready to play
     */
    on_game_join(ev)
    {
        this.friend = {name: ev.detail.other_player};
        this.player.order = ev.detail.player_order;
        this.elements.opponent_name.innerText = ev.detail.other_player;
        this.elements.opponent_text.style.display = "block";
        this.elements.button_restart.style.display = "none";

        for ( let i = 0; i < 9; i++ )
        {
            let cell = this.elements.cells[i];
            cell.classList.remove("winning");
        }

        this.switch_screen("game");
    }

    /**
     * \brief Successfully created a game
     */
    on_game_created(ev)
    {
        this.game_id = ev.detail.id;
        this.elements.new_game_id.innerText = ev.detail.id;
        this.switch_screen("new-game");
    }

    /**
     * \brief Leaving game, back to start
     */
    on_game_leave(ev)
    {
        this.switch_screen("start");
        this.friend = null;
    }

    /**
     * \brief Update the game board
     */
    on_game_state(ev)
    {
        this.game = ev.detail;

        if ( this.game.turn == this.player.order )
        {
            this.elements.board.classList.remove("waiting");
            this.elements.turn.innerText = "Your turn!";
        }
        else
        {
            this.elements.board.classList.add("waiting");
            this.elements.turn.innerText = this.game.turn_name + "'s turn";
        }

        for ( let i = 0; i < 9; i++ )
        {
            let cell = this.elements.cells[i];
            cell.innerText = ev.detail.table[i];
            if ( ev.detail.table[i] == "" )
                cell.classList.add("empty");
            else
                cell.classList.remove("empty");
        }

        if ( this.game.finished )
        {
            this.elements.board.classList.remove("waiting");

            if ( this.game.turn == this.player.order )
                this.elements.turn.innerText = "You won!";
            else
                this.elements.turn.innerText = ev.detail.winner + " won!";
            this.elements.opponent_text.style.display = "none";
            this.elements.button_restart.style.display = "block";

            for ( let i of ev.detail.triplet )
            {
                let cell = this.elements.cells[i];
                cell.classList.add("winning");
            }

            for ( let i = 0; i < 9; i++ )
            {
                let cell = this.elements.cells[i];
                cell.classList.remove("empty");
            }
        }

        this.switch_screen("game");
    }

    /**
     * \brief Join request failed
     */
    on_join_fail(ev)
    {
        this.elements.request_error.style.display = "block";
        this.elements.request_error.innerText = "Could not join game, try a different code";
        this.switch_screen("start");

    }

    /**
     * \brief Host receives a join request
     */
    on_join_request(ev)
    {
        this.friend = ev.detail;
        this.elements.request_name.innerText = ev.detail.name;
        this.switch_screen("request-received");
    }

    /**
     * \brief Server acknowledges a game.join request
     */
    on_join_sent(ev)
    {
        this.switch_screen("request-sent");
    }

    /**
     * \brief Sends moves to the server when a game cell is clicked
     */
    on_cell_clicked(ev)
    {
        this.connection.send({type: "game.move", cell: Number(ev.target.dataset.index)});
    }
}
