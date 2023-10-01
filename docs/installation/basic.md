Basic Installation
==================

## Overview

This project consists of a server-side app written in python that is exposed
as a web socket, and a static html page that communicates with the web socket.

They both have a JSON with settings so you can configure it to your needs.

The following guide shows how to install and configure the various tools
on a Ubuntu server.

This guide assumes the domain is `miniapps.example.com`, replace with the
appropriate value in the various config files.

Most steps require to have root access on a default configuration, if you are
not logged in as `root`, you can try `sudo`.


This guide will install the mini app in `/var/www/miniapps.example.com`,
you might want to use a different directory.


There are [multiple apps](../apps/index.md) available, this guide will set up
the [mini events](../apps/mini_event.md) app, but you can easily add more apps.

## Bot Setup

Please refer to the [Mini Event setup guide](../apps/mini_event.md#bot-setup).

## Installing the Code

This guide will install the mini app in `/var/www/miniapps.example.com`,
you might want to use a different directory.


Ensure the project is installed in a directory that apache can serve,

If you want to use git to install the project, use the following commands:
```bash
cd /var/www/
git clone https://github.com/mbasaglia/mini_apps.git miniapps.example.com
```


## Configuration

Add the settings file for the client `/var/www/miniapps.example.com/client/settings.json`
with the following content:

```json
{
    "socket": "wss://miniapps.example.com/wss/"
}
```

And the server-side settings file `/var/www/miniapps.example.com/server/settings.json`
with the following:

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

Explanation of the settings fields:

* `database`: This configures the database connection
    * `class`: One of the [Peewee database classes](https://docs.peewee-orm.com/en/latest/peewee/database.html)
    * The rest of the properties here are passed as class constructor arguments
* `log`: Configures app logging, everything here corresponds to Python's [logging.basicConfig](https://docs.python.org/3/library/logging.html#logging.basicConfig)
* `websocket`: Web socket settings
    * `hostname`: Socket bind host name or address
    * `port`: Socket port
* `apps`: Map of app short name to app settings. App settings contain the following:
    * `class`: Python class that runs the bot / app
    * `session`: (Optional) [session name](https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.telegrambaseclient.TelegramBaseClient) for Telethon
    * `bot-token`: Bot API token as kiven by BotFather
    * `url`: URL of the mini app main page
    * `media-url`: Base URL for images
* `api-id`: MTProto API ID, you can get its value from <https://my.telegram.org/apps>
* `api-hash`: MTProto API hash, you can get its value from <https://my.telegram.org/apps>

If you want to run on the Telegram test server, add the following to the JSON,
with the values from <https://my.telegram.org/apps>.

```js
"telegram-server": {
    "dc": 2,
    "address": "127.0.0.1",
    "port": 443
}
```


## Permissions

The media directory in the client needs to be writable by the web server:

```bash
chgrp www-data /var/www/miniapps.example.com/client/media/
chmod g+w /var/www/miniapps.example.com/client/media/
```


## Running Docker

This section shows how to run containers to run the mini apps.
If you instead want to run the apps your machine directly (without docker)
you can follow the instructions for an [advanced installation](./advanced.md).


You need to have `docker-compose` installed on the system:

```bash
apt install -y docker-compose git
```

There is a docker-compose file that wraps the all services as containers.

To start the container simply run the following:

```bash
cd /var/www/var/www/miniapps.example.com
docker-compose up -d
```

This will make the app accessible from `http://localhost:2537/`. You might want to add a web server on top of it
to expose it to the public with your domain name and set up SSL certificates for a secure connection.
You can follow the [advanced front-end instructions] (./advanced.md#front-end-apache) for details.
