Making Your Own App
===================


This guide describes how to make custom bots / mini apps.

We will create a new app called `MyApp` that does absolutely nothing useful!


Basic Setup
-----------


### Prerequisites

Ensure you have a bot registered to [BotFather](https://t.me/BotFather), also
ensure you followed all the installation steps.


### Server Side Code

At minimum you need a Python class that inherits `mini_apps.app.App`.

Create a python file as `server/mini_apps/my_app.py` with the following content:

```py
from .app import App


class MyApp(App):
    pass
```

In `server/settings.json` add a new app like so:

```js
{
    ...

    "apps": {
        "my_app": {
            "class": "mini_apps.my_app.MyApp",
            "bot-token": "(your bot token)",
            "api-id": "(your api id)",
            "api-hash": "(your api hash)",
            "url": "https://miniapps.example.com/myapp.html",
            "media-url": "https://miniapps.example.com/media/"
        }
    }
}
```

Then restart the server script. If you're using docker-compose, run

```bash
docker-compose restart miniapp
```

Now technically the app is running but it doesn't have any front-end page nor
any logic to it.


### Front-End

First we need the JavaScript code that handles the client-side logic.

Create the file `client/src/myapp.js` with the following contents:

```js
import { App } from "./app.js";


export class MyApp extends App
{
    constructor(telegram)
    {
        // `myapp` here is the App ID as from the server settings
        super("myapp", telegram);
    }
}
```

Then we will create the frontent page as `client/myapp.html` (the file
name must match what you have as `url` in the server settings).

```html
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>
    <!-- This makes sure it scales properly on mobile -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <!-- Script to communicate with telegram -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <!-- This CSS sets up some basic styling using the telgram theme -->
    <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body>
    <main>
        <div id="content">Hello!</div>
    </main>

    <script type="module">
        import { MyApp } from "./src/myapp.js";

        const myapp = new MyApp(window.Telegram);

        myapp.connect_from_settings();

        // This makes it easier to debug on the browser console
        window.myapp = myapp;
    </script>
</body>
</html>
```

Connecting Telegram
-------------------

Now the basic app is set up, even if it doesn't do anything.

There are [several ways](https://core.telegram.org/bots/webapps#implementing-mini-apps)
you can launch a mini app from Telegram, here we will set up a
[direct link](https://core.telegram.org/bots/webapps#direct-link-mini-apps).


### BotFather

Talk to [BotFather](https://t.me/BotFather) and send it the `/newapp`
command, follow its isntruction making sure you use the url as per settings.

Now clicking on the link that BotFather gives you at the end should show the
"Hello!" message from the app.


### Showing a start message

Now, it's useful to show a start message and a button to start the mini app
when a user starts a chat with your bot, this is fairly simple to do.

Modify `my_app.py` as follows:

```py
import inspect
import telethon

from .app import App


class MyApp(App):
    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Start",
                    self.settings.url
                )
            ])
        ])

    async def on_telegram_start(self, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        This bot does absolutely nothing useful
        """), buttons=self.inline_buttons())
```

The code to add an inline button is a bit verbose but everything else should be
rather striaghtforward.

Restart the server again, and you should be able to see that message on your
bot chat log after you send `/start`.


Websocket Communication
-----------------------

At this point the server app runs the telegram bot and the html is a static page.

The two can communicate by sending messages through websocket.

All the complexity of setting up the communication is already handled by the
existing code so the only thing we need to do is add logic to it.


### Greeting the User

Telegram sends some information about the connected user to the web app.

This is validated by the server and user details are sent back through the websocket
with a `welcome` message.

We can change the JavaScript code to show a personalized greeting when this happens.

```js
import { App } from "./app.js";


export class MyApp extends App
{
    constructor(telegram)
    {
        super("myapp", telegram);
    }

    /**
     * Called when the server sends user details
     */
    _on_welcome(ev)
    {
        super._on_welcome(ev);
        document.getElementById("content").innerText = `Hello ${ev.detail.name}!`;
    }
}
```


### Useless Button

Now we will set up a button that shows the number of times it has been pressed
by users.

Let's add the button to the html, and add an event that calls a method on the app:

```html
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>
    <!-- This makes sure it scales properly on mobile -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <!-- Script to communicate with telegram -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <!-- This CSS sets up some basic styling using the telgram theme -->
    <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body>
    <main>
        <div id="content">Hello!</div>
        <p class="buttons">
            <button id="my_button">0</button>
        </p>
    </main>

    <script type="module">
        import { MyApp } from "./src/myapp.js";

        const myapp = new MyApp(window.Telegram);

        myapp.connect_from_settings();

        // This makes it easier to debug on the browser console
        window.myapp = myapp;

        // Call myapp.on_click() when the button is clicked
        document.getElementById("my_button").addEventListener(
            "click", myapp.on_click.bind(myapp)
        );
    </script>
</body>
</html>
```

On the JS code we add said method and we send a message to the server,
and we add a handler for the server message that updates the number of clicks in
real time:


```js
import { App } from "./app.js";


export class MyApp extends App
{
    constructor(telegram)
    {
        super("myapp", telegram);

        // When we receive a "clicks-updated" message from the server,
        // we call myapp.on_clicks_updated
        this.connection.addEventListener("clicks-updated", this.on_clicks_updated.bind(this));
    }

    _on_welcome(ev)
    {
        super._on_welcome(ev);
        document.getElementById("content").innerText = `Hello ${ev.detail.name}!`;
    }

    on_click()
    {
        // Just send a simple message to the server
        this.connection.send({
            type: "click",
            // You can add more data here if you need to
            custom_data: 123,
        });
    }

    on_clicks_updated(ev)
    {
        // Update the text of the button
        document.getElementById("my_button").innerText = ev.detail.count;
    }
}
```

Finally, we update the server-side code:

```py

import inspect
import telethon

from .app import App


class MyApp(App):
    def __init__(self, *args):
        super().__init__(*args)
        # Click count, this resets when the server restarts
        self.click_count = 0

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Start",
                    self.settings.url
                )
            ])
        ])

    async def on_telegram_start(self, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        This bot does absolutely nothing useful
        """), buttons=self.inline_buttons())

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        # Send the initial count when the client connects
        await client.send(type="clicks-updated", count=self.click_count)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        # Here you can access additional data as data["custom_data"]
        if type == "click":
            # Increment count
            self.click_count += 1
            # Update on all clients
            for client in self.clients.values():
                await client.send(type="clicks-updated", count=self.click_count)
        else:
            await client.send(type="error", msg="Unknown command", what=data)
```


Once you restart the server, the button will update whenever someone clicks it.


Further Steps
-------------

This is just a basic example, there is so much more you can do with this system.

The following sections will not give a full tutorial but will show snippets of
how various common features are implemented.


### Database Storage

You can store data in the database, by defining your own models.

It's important that you inherit from `mini_apps.db.BaseModel` but otherwise
they are simple [Peewee Models](https://docs.peewee-orm.com/en/latest/peewee/models.html).

Also you need to register models on your app:

```py
from .app import App
from .db import BaseModel


class Button(BaseModel):
    count = peewee.IntegerField()



class MyApp(App):
    def register_models(self):
        """
        Registers the database models
        """
        self.settings.databse_models += [Button]
```

### Inline Queries

You can trigger inline queries from JavaScript with:

```js
this.webapp.switchInlineQuery(`(query)`, ["users", "groups", "channels"]);
```

To handle the request, you need to add a method to MyApp in Python

```python
import telethon

from .app import App

class MyApp(App):
    async def on_telegram_inline(self, query: telethon.events.InlineQuery):
        """
        Called on telegram bot inline queries
        """

        results = []

        text = "You entered %s" % query.text

        results.append(query.builder.article(
            title=text,
            text=text
        ))

        await query.answer(results)
```
