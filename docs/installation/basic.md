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

Some require to have root access, if you are not logged in as `root`, you can try `sudo`.


This guide will install the mini app in `/opt/miniapps.example.com`, you might want to use a different directory.
If you are planning to run from docker, somewhere in your home directory will also work.


There are [multiple apps](../apps/index.md) available, this guide will set up
the [Tic Tac Toe](../apps/tic_tac_toe.md) app, but you can easily add more apps.


## Bot Setup

Talk to [BotFather](https://t.me/BotFather) and create a bot, keep note of the token it gives you as it's needed later.

On that bot enable the _Menu Button_ under _Bot Settings_, and give it `https://miniapps.example.com/tic_tac_toe/` as URL.

You need to create a new app on that bot (`/newapp`) with the same URL as the button, and `tic_tac_toe` short name.

Finally, enable inline mode with `/setinline`.


## Installing the Code

This guide will install the mini app in `/opt/miniapps.example.com`,
you might want to use a different directory.


Ensure the project is installed in a directory that apache can serve,

If you want to use git to install the project, use the following commands:
```bash
cd /opt/
git clone https://github.com/mbasaglia/mini_apps.git miniapps.example.com
```


## Configuration

Add the settings file for the client `/opt/miniapps.example.com/client/settings.json`
with the following content:

```json
{
    "socket": "wss://miniapps.example.com/wss/"
}
```

And the server-side settings file `/opt/miniapps.example.com/src/settings.json`
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
        "tic_tac_toe": {
            "class": "mini_apps.apps.tic_tac_toe.TicTacToe",
            "bot-token": "(your bot token)",
            "short-name": "tic_tac_toe",
            "url": "https://miniapps.example.com/tic_tac_toe/"
        }
    },
    "api-id": "(your api id)",
    "api-hash": "(your api hash)"
}
```
The value for `bot-token` is the bot API token given by BotFather.

The values for `api-id` and `api-hash` can be obtained from <https://my.telegram.org/apps>.

`url` should be the public URL of your mini app, the same you specified on BotFather.

`short-name` is the app short name that you set on BotFather with `/newapp`.

If you want to run on the Telegram test server, add the following to the JSON,
with the values from <https://my.telegram.org/apps>.

```js
"telegram-server": {
    "dc": 2,
    "address": "127.0.0.1",
    "port": 443
}
```

For more detailed documentation on all the available settings see [Settings](./settings.md).


## Running Docker

This section shows how to run containers to run the mini apps.
If you instead want to run the apps directly on your machine (without docker)
you can follow the instructions for an [advanced installation](./advanced.md).


You need to have `docker-compose` installed on the system:

```bash
apt install -y docker.io docker-compose git
```

Instead of `apt` you can also follow the official installation instructions for docker
[engine](https://docs.docker.com/engine/install/) and [compose](https://docs.docker.com/compose/install/).

Your user might need to be in the `docker` group, for more details see the
[docker documentation](https://docs.docker.com/engine/install/linux-postinstall/).

There is a docker-compose file that wraps the all services as containers.

To start the container simply run the following:

```bash
cd /opt/miniapps.example.com
docker-compose up -d
```

This will make the app accessible from `http://localhost:2537/`. You might want to add a web server on top of it
to expose it to the public with your domain name and set up SSL certificates for a secure connection.
You can follow the [advanced front-end instructions](./advanced.md#front-end-apache) for details.
