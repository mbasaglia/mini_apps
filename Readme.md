Event Telegram Mini-App Demo
============================

This is a demo of telegram mini apps.

It shows a list of events the user can attend and uses websockets to dynamically
update information to the client.


Installation
------------

### Bot Setup

You need to have a bot for mini apps to work. Talk to [BotFather](https://t.me/BotFather)
to create the bot. Make sure you enable inline mode and the menu button in the
bot settings.

Use `/newapp` to create a web app on the bot and give it `events` as short name.

Also, do keep track of the bot token as it's needed in the server
configuration file.

### Installation Overview

This project consists of a server-side app written in python that is exposed
as a web socket, and a static html page that communicates with the web socket.

They both have a JSON with settings so you can configure it to your needs.

The following guide shows how to install and configure the various tools
on a Ubuntu server with Apache.

This gues assumes the domain is `miniapps.example.com`, replace with the
appropriate value in the various config files.

Most steps require to have root access on a default configuration, if you are
not logged in as `root`, you can try `sudo`.

### Installing Dependencies

We need Apache to run the web server, docker-compose to run
the web socket code.


```bash
apt install -y apache2 docker-compose git
```

### Configuration

Ensure the project is installed in a directory that apache can serve,

If you want to use git to install the project, use the following commands:
```bash
cd /var/www/
git clone https://github.com/mbasaglia/mini_apps.git miniapps.example.com
```

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
        "class": "SqliteDatabase",
        "database": "db/db.sqlite"
    },
    "websocket": {
        "hostname": "localhost",
        "port": 2536
    },
    "apps": {
        "events": {
            "class": "mini_apps.mini_event.MiniEventApp",
            "bot-token": "(your bot token)",
            "api-id": "(your api id)",
            "api-hash": "(your api hash)",
            "url": "https://miniapps.example.com/events.html",
            "media-url": "https://miniapps.example.com/media/"
        }
    }
}
```

Explanation of the settings fields:

* `database`: This configures the database connection
    * `class`: One of the [Peewee database classes](https://docs.peewee-orm.com/en/latest/peewee/database.html)
    * The rest of the properties here are passed as class constructor arguments
* `websocket`: Web socket settings
    * `hostname`: Socket bind host name or address
    * `port`: Socket port
* `apps`: Map of app short name to app settings. App settings contain the following:
    * `class`: Python class that runs the bot / app
    * `api-id`: MTProto API ID, you can get its value from https://my.telegram.org/apps
    * `api-hash`: MTProto API hash, you can get its value from https://my.telegram.org/apps
    * `session`: (Optional) [session name](https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.telegrambaseclient.TelegramBaseClient) for Telethon
    * `bot-token`: Bot API token as kiven by BotFather
    * `url`: URL of the mini app page
    * `media-url`: URL used to host images and the like


### Permissions

The media directory in the client needs to be writable by the web server:

```bash
chgrp www-data /var/www/miniapps.example.com/client/media/
chmod g+w /var/www/miniapps.example.com/client/media/
```

### Back-End With Docker

There is a docker-compose file that wraps the back-end service as a container.

To start the container simply run the following:

```bash
cd /var/www/var/www/miniapps.example.com
docker-compose up -d
```

If you want to install the back-end on your machine directly (without docker)
you can follow the instructions for a [manual installation](./docs/manual-installation.md).

### Front-End With Apache

This step is what makes the app accessible from outside the server machine.
To ensure everything is secured, we'll use `certbot` to generate certificates.

Create a new site on apache as `/etc/apache2/sites-available/minievent.evample.com.conf`:

```apache
# This sets up the SSL (ecrypted) virtual host, which actually hosts the website
<VirtualHost *:443>
    # Basic Setup (domain and directory)
    ServerName minievent.evample.com
    DocumentRoot /var/www/minievent.evample.com/client

    # Makes the local websocket available as wss://minievent.evample.com/wss/
    ProxyRequests Off
    ProxyPass /wss/ ws://localhost:2536

    # SSL settings
    SSLEngine on
    SSLCertificateFile      /etc/letsencrypt/live/minievent.evample.com/cert.pem
    SSLCertificateKeyFile   /etc/letsencrypt/live/minievent.evample.com/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/minievent.evample.com/chain.pem
    Header always set Strict-Transport-Security "max-age=2678400"
</VirtualHost>

# This is the non-encrypted virtual host, which redirects all requests from http to https
# only giving access to the certbot
<VirtualHost *:80>
    ServerName minievent.evample.com

    <Location ~ "^(?!/.well-known)">
        Redirect permanent / "https://minievent.evample.com/"
    </Location>

    Alias "/.well-known" "/var/www/minievent.evample.com/.well-known"
    <Directory /var/www/minievent.evample.com/.well-known>
        Allow from all
        Options -Indexes
    </Directory>
</VirtualHost>
```

Enable the new site and restart Apache

```bash
a2ensite minievent.evample.com
apache2ctl restart
```

Follow the installation instructions for `certbot` at https://certbot.eff.org/instructions?ws=apache&os=ubuntufocal

To generate the certificates you can use the following command:

```bash
certbot --authenticator webroot --installer apache certonly -w /var/www/miniapps.example.com --domains miniapps.example.com
```

Loading Data
------------

There are a couple of server-side scripts that allow you to add some data into the system:

`server/add_event.py` `-t` _title_ `-d` _description_ `-s` _start-time_ `-r` _duration_ `-i` _image_<br/>
This is used to add more events to the database, you pass the image by path
and it will be copied over to the media directory. Note that images should
be less that 512 KB in size, have a 16:9 aspect ratio and should be at least 400 pixels wide.

`server/list_users.py`<br/>
Shows a list of users, with their telegram ID, admin status and name.

`server/make_admin.py` _telegram-id_<br/>
Makes a user an admin (creating the user if it doesn't exist).
You can use `server/list_users.py` to find the right telegram ID.

All these scripts support the `--help` command that gives more details on how they work.

Please note that this demo uses SQLite to minimize set up and it only supports a single
connection at a time. So if you want to call any of these scripts, you need to stop the server.


Customizing
-----------

To make your own MiniApp, see [Making Your Own App](./docs/custom-app.md).

Admin Interface
---------------

If you created admin users (with `server/make_admin.py`), when those users
access the mini app, they will see additional options, which allows them to manage
the events.


Web Socket Messages
-------------------

This section will describe the messages sent through web sockets.
All the messages are JSON-encoded, and have a `type` attribute that determintes
the kind of message.

Messages sent from the client, have an `app` attribute to identify which app the message is delivered to.

Connection-related messages:

* `connect`: Sent by the server on connection, notifies the client the server can accept messages
* `login`: Sent by the client, including the telegam mini app authentication data
* `disconnect`: Sent by the server if the `login` failed
* `welcome`: Sent by the server if the `login` succeeded, this includes the telegram id and name
* `error`: Sent by the server to notify the client of some kind of error. It includes the error message.

Messages specific to the Mini Event data:

* `event`: Sent by the server when there is a new event available
(or an existing event has been modified). It's also sent after welcome to give all the existing events.
This includes all the event-specific data.
* `attend`: Sent by the client to register attendance to an event, it includes the event ID.
* `leave`: Sent by the client to cancel attendance to an event, it includes the event ID.
