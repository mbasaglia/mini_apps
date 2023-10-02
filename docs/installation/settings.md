Settings
========

This page describes in detail all the available settings in the `settings.json` files.

Client
------

The client-side `settings.json` only has a single property that specifies the websockets apps connect to.

Example:

```json
{
    "socket": "ws://localhost:2536/"
}
```

Server
------

Server-side configuration is more involved, everything will be described in the appropriate section.

| Property  | Type      |Default| Description                       |
|-----------|-----------|-------|-----------------------------------|
|`database` | `object`  |       | Database settings                 |
|`log`      | `object`  | `{}`  | Logging configuration             |
|`websocket`| `object`  |       | Websocet settings                 |
|`apps`     | `apps`    |       | Available apps and their settings |
|`reload`   | `boolean` |`false`| If `true`, [server/server.py](../scripts.md#server-server-py) will reload when the sources change |


Example:


```json
{
    "database": {
        "class": "peewee.SqliteDatabase",
        "database": "db/db.sqlite"
    },
    "log": {
        "level": "INFO"
    },
    "websocket": {
        "hostname": "localhost",
        "port": 2536
    },
    "apps": {
        "mini_event": {
            "class": "mini_apps.apps.mini_event.MiniEventApp",
            "bot-token": "(your bot token)",
            "url": "https://miniapps.example.com/mini_event/",
            "media-url": "https://miniapps.example.com/media/"
        }
    },
    "api-id": "(your api id)",
    "api-hash": "(your api hash)"
}
```


### `database`

Database settings, `class` is one of the One of the [Peewee database classes](https://docs.peewee-orm.com/en/latest/peewee/database.html).
The rest of the properties here are passed as class constructor arguments.

For `peewee.SqliteDatabase`, `database` can be a path (if relative, it will be considered relative from the root of the project).
or the string `:memory:`.

Example:

```json
{
    "class": "peewee.SqliteDatabase",
    "database": "db/db.sqlite"
}
```

### `log`

Logging configuration most entries here correspond to Python's [logging.basicConfig](https://docs.python.org/3/library/logging.html#logging.basicConfig).

* `level`: Log level for mini-app-specific loggers.
* `global-level`: Logging level for all other loggers registered in Python's logging.

Example:

```json
{
    "level": "DEBUG",
    "global-level": "WARN",
    "format": "%(asctime)s %(name)-10s %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S"
}
```

### `websocket`

Web socket server settings.

* `hostname`: Socket bind host name or address, to accept remote connections use `0.0.0.0`,
otherwise `localhost` should work in most cases.
* `port`: Socket TCP port

Example:

```json
{
    "hostname": "localhost",
    "port": 2536
}
```


### `apps`

An object where the keys serve as App identifiers, and the values are app-specific settings.

This section will describe all the common app settigs, but some apps might require additional
settings, refer to each [app documentation](../apps/index.md) for details.

Follows a table with all the available settings, anything without a _Default_ is required.

| Property          | Type      |Default| Description                                                                   |
|-------------------|-----------|-------|-------------------------------------------------------------------------------|
|`enabled`          | `boolean` | `true`| If `false`, the app will not be loaded                                        |
|`class`            | `string`  |       | Python class that runs the bot / app                                          |
|`api-id`           | `integer` |       | MTProto API ID, you can get its value from <https://my.telegram.org/apps>     |
|`api-hash`         | `string`  |       | MTProto API hash, you can get its value from <https://my.telegram.org/apps>   |
|`telegram-server`  | `object`  | `null`| MTProto server settings, described in detail later                            |
|`session`          | `string`  | `null`| [session name](https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.telegrambaseclient.TelegramBaseClient) for Telethon |
|`url`              | `string`  | `""`  | Public URL for the app, used to generate webview buttons                      |
|`fake-user`        | `object`  | `null`| For debugging purposes, allows login from a browser without Telegram webview  |

Example:

```json
{
    "class": "mini_apps.apps.mini_event.MiniEventApp",
    "bot-token": "(your bot token)",
    "url": "https://miniapps.example.com/mini_event/",
    "media-url": "https://miniapps.example.com/media/"
}
```

#### `telegram-server`

Mostly needed if you want to run on the Telegram test server, with the values from <https://my.telegram.org/apps>.

Example:

```json
{
    "dc": 2,
    "address": "127.0.0.1",
    "port": 443
}
```

#### `fake-user`

Debug user for accessing the  app without telegram, it should only be used for local development!

| Property      | Type     |Default | Description   |
|---------------|----------|--------|---------------|
|`id`           | `number` |        | Telegram ID   |
|`first_name`   | `string` |        | First name    |
|`last_name`    | `string` | `""`   | Last name     |

Example:

```json
{
    "id": 12345,
    "first_name": "Test"
}
```

#### Default App Settings

Note that some settings like `api-id`, `api-hash`, `telegram-server` might be fixed for multiple apps.

So instead of repeating them for each app, you can specify them at the top level of the JSON, and they will be available
for all apps. Each app can then override them by having specific values in their own settings.

Example:

```json
{
    "apps": {
        "mini_event": {
            "class": "mini_apps.apps.mini_event.MiniEventApp",
            "session": "minievent",
            "media-url": "http://localhost:2537/media/",
            "url": "http://localhost:2537/mini_event/"
        },
        "glaximini": {
            "class": "mini_apps.apps.glaximini.app.Glaximini",
            "url": "http://localhost:2537/glaximini/"
        }
    },
    "api-id": "(your api id)",
    "api-hash": "(your api hash)",
    "telegram-server": {
        "dc": 2,
        "address": "127.0.0.1",
        "port": 443
    }
}
```
