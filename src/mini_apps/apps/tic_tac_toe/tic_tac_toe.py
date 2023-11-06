import inspect
import random

import hashids

from mini_apps.telegram.bot import TelegramMiniApp, bot_command
from mini_apps.telegram.utils import InlineKeyboard
from mini_apps.telegram.events import NewMessageEvent, InlineQueryEvent
from mini_apps.http.web_app import ExtendedApplication, template_view
from mini_apps.service import Client


id_encoder = hashids.Hashids("tictactoe", alphabet="abcdefhkmnpqrstuvwxy34578")


class Player:
    """
    Keeps track of a player's status
    """
    def __init__(self, client: Client):
        self.game = None
        self.user = client.user
        self.client = client
        self.id = client.user.telegram_id
        self.requested = None
        self.player_order = -1

    async def send(self, **kwargs):
        """
        Sends a message to the player
        """
        # TODO send something on telegram if the client isn't online
        if self.client:
            await self.client.send(**kwargs)


class Game:
    triplets = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),

        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),

        (0, 4, 8),
        (2, 4, 6),
    ]

    def __init__(self, host: Player):
        self.host: Player = host
        self.guest: Player = None
        self.requests = {}
        self.table = [""] * 9
        self.winner = None
        self.id = id_encoder.encode(host.user.telegram_id)
        self.turn = -1
        self.winning_cells = None
        self.free = 9

    def turn_name(self):
        """
        Name of the player whose turn it is
        """
        if self.turn == 0:
            return self.host.user.name
        elif self.turn == 1:
            return self.guest.user.name
        return ""

    def is_host(self, player: Player):
        """
        Whether a player is the host
        """
        return player.id == self.host.id

    async def send_state(self, player: Player):
        """
        Sends the game state to a player
        """
        await player.send(
            type="game.state",
            turn=self.turn,
            table=self.table,
            turn_name=self.turn_name(),
            finished=self.winner is not None,
            winner=self.winner,
            triplet=self.winning_cells
        )

    async def send_queued_request(self):
        """
        Sends the next queued request
        """
        if self.requests:
            player = next(iter(self.requests.values()))
            self.requests.pop(player.user.telegram_id)
            await self.host.send(type="join.request", id=player.user.telegram_id, name=player.user.name)

    async def send_to_player(self, player: Player):
        """
        Sends the right message to a player
        """
        if self.winner is not None:
            await self.send_state(player)
        elif self.is_host(player):
            if self.guest:
                player.player_order = 0
                await player.send(type="game.join", id=self.id, other_player=self.guest.user.name, player_order=0)
                await self.send_state(player)
            else:
                await player.send(type="game.created", id=self.id)
                await self.send_queued_request()
        elif player.id == self.guest.id:
            player.player_order = 1
            await player.send(type="game.join", id=self.id, other_player=self.host.user.name, player_order=1)
            await self.send_state(player)
        else:
            await player.send(type="error", msg="Not in this game")
            await player.send(type="game.leave")

    async def move(self, player: Player, cell: int):
        """
        Make a move on the player
        """
        if self.winner is not None or player.player_order != self.turn or cell < 0 or cell >= 9 or self.table[cell] != "":
            return

        self.free -= 1
        self.table[cell] = "XO"[player.player_order]
        self.turn = (self.turn + 1) % 2

        winners = set()
        for triplet in self.triplets:
            if self.check_same(triplet):
                winners |= set(triplet)

        if winners:
            self.winner = player.user.name
            self.turn = player.player_order
            self.winning_cells = list(winners)

        elif self.winner is None and self.free <= 0:
            self.winner = "No one"
            self.winning_cells = []

        await self.send_state(self.host)
        await self.send_state(self.guest)

    def check_same(self, triplet):
        """
        Checks for wins
        """
        a = self.table[triplet[0]]
        if a == "":
            return False

        b = self.table[triplet[1]]
        if b == "" or a != b:
            return False

        c = self.table[triplet[2]]
        if c == "" or c != b:
            return False

        return True


class TicTacToe(TelegramMiniApp):
    """
    Tic Tac Toe Game
    """
    def __init__(self, *args):
        super().__init__(*args)
        self.players = {}

    @template_view("/", template="tic_tac_toe.html")
    async def index(self, request):
        return {
            "socket": self.http.websocket_url
        }

    def prepare_app(self, http, app: ExtendedApplication):
        """
        Registers routes to the web server
        """
        super().prepare_app(http, app)
        app.add_static_path("/tic_tac_toe.js", self.get_server_path() / "tic_tac_toe.js")

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        kb = InlineKeyboard()
        kb.add_button_webview("Play", self.url)
        return kb.to_data()

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        player: Player = self.players.get(client.user.telegram_id)
        if not player:
            player = Player(client)
            self.players[client.user.telegram_id] = player
        else:
            player.client = client

        client.player = player
        if player.game:
            await player.game.send_to_player(player)
        else:
            join_request = client.user.telegram_data.get("start_param", None)
            if join_request:
                await self.send_join_request(player, join_request)

    async def send_join_request(self, player: Player, game_id: str):
        """
        Sends a request from a player to join a specified game
        """
        if player.game:
            # Player is already playing the game
            if player.game.host or player.game.id == game_id:
                await player.game.send_to_player(player)
                return

        try:
            host_id = id_encoder.decode(game_id)[0]
        except Exception:
            await player.send(type="join.fail")
            return

        host = self.players.get(host_id)
        if not host:
            await player.send(type="join.fail")
            return

        game: Game = host.game
        if not game or game.guest or game.is_host(player) or game.winner is not None:
            await player.send(type="join.fail")
            return

        player.requested = game.id
        await player.send(type="join.sent")

        if host.client:
            await host.send(type="join.request", id=player.user.telegram_id, name=player.user.name)

        elif player.user.telegram_id not in game.requests:
            game.requests[player.user.telegram_id] = player
            try:
                await self.telegram.send_message(
                    host.user.telegram_id,
                    "**{name}** wants to play Tic Tac Toe with you".format(name=player.user.name),
                    buttons=self.inline_buttons()
                )
            except Exception:
                self.log_exception()

    @bot_command("start", description="Start message")
    async def on_telegram_start(self, args: str, event: NewMessageEvent):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        Tic Tac Toe game against another player on telegram
        """), buttons=self.inline_buttons())

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        if client.player:
            client.player.client = None
            # TODO update online status for the other player (if any)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        game = client.player.game

        # A user creates a new game
        if type == "game.new":
            if not game:
                game = Game(client.player)
                client.player.game = game
                client.player.requested = None
            await game.send_to_player(client.player)

        # A user leaves / cancels the game
        elif type == "game.leave":
            if game:
                if game.is_host(client.player):
                    if game.guest:
                        game.guest.game = None
                        await game.guest.send(type="game.leave")
                else:
                    game.guest = None

                client.player.game = None

        # A user wants to join an existing game
        elif type == "game.join":
            await self.send_join_request(client.player, data.get("game"))

        # Join request accepted
        elif type == "join.accept":
            guest = self.players.get(data.get("who"))
            if not game or not guest or guest.game or guest.requested != game.id:
                return

            guest.game = game
            game.guest = guest
            game.turn = random.randint(0, 1)
            await game.send_to_player(client.player)
            await game.send_to_player(guest)

        # Join request rejected
        elif type == "join.refuse":
            guest = self.players.get(data.get("who"))
            if not game or not guest or guest.game or guest.requested != game.id:
                return
            await guest.send(type="join.fail")
            # Show next request (if any)
            await game.send_queued_request()

        # A user makes a move
        elif type == "game.move":
            if game:
                try:
                    cell = int(data["cell"])
                except Exception:
                    return

                await game.move(client.player, cell)

                if game.winner is not None:
                    game.guest.game = None
                    game.host.game = None

    async def on_telegram_inline(self, query: InlineQueryEvent):
        """
        Called on telegram bot inline queries
        """
        results = []

        player = self.players.get(query.query.user_id)
        if player and player.game and player.game.is_host(player) and not player.game.guest:
            results.append(query.builder.article(
                title="Send Code",
                description=player.game.id,
                text="[Play Tic Tac Toe with me!](https://t.me/{me}/{shortname}?startapp={id})".format(
                    me=self.telegram_me.username,
                    shortname=self.settings.get("short_name", self.name),
                    id=player.game.id
                )
            ))

        await query.answer(results)
