Event Telegram Mini-App Demo
============================

This is a demo of telegram mini apps.

It shows a list of events the user can attend and uses websockets to dynamically
update information to the client.


Installation
------------

### Installation Overview

This project consists of a server-side app written in python that is exposed
as a web socket, and a static html page that communicates with the web socket.

They both have a JSON with settings so you can configure it to your needs.

The following guide shows how to install and configure the various tools
on a Ubuntu server with Apache.

This gues assumes the domain is `minievent.example.com`, replace with the
appropriate value in the various config files.

Most steps require to have root access on a default configuration, if you are
not logged in as `root`, you can try `sudo`.

### Installing Dependencies

We need Apache to run the web server, python, virtualenv, and supervisor to run
the web socket code.


```bash
apt install -y apache2 python3 python3-virtualenv supervisor git
```

### Configuration

Ensure the project is installed in a directory that apache can serve,

If you want to use git to install the project, use the following commands:
```bash
cd /var/www/
git clone https://github.com/mbasaglia/mini_event.git minievent.example.com
```

Add the settings file for the client `/var/www/minievent.example.com/client/settings.json`
with the following content:

```json
{
    "socket": "wss://minievent.example.com/wss"
}
```

And the server-side settings file `/var/www/minievent.example.com/server/settings.json`
with the following, taking care of setting `bot-token` with the telegram bot token
given by BotFather:

```json
{
    "hostname": "localhost",
    "port": 2536,
    "database": "db/db.sqlite",
    "bot-token": "(your token)"
}
```

### Python Dependencies

Set up a virtual environment and install dependencies:

```
cd /var/www/minievent.example.com
virtualenv env
pip install -r server/requirements
```

### Supervisor

Supervisor is a tool that allows you to keep running scripts in the background,
and it provides commands to start and stop them. Here we use it to run the
python script that manages the server-side web socket.

The supervisor config will be in `/etc/supervisor/conf.d/minievent.conf`
with the following content:

```
[program:minievent]
user=www-data
group=www-data
stderr_logfile=/var/log/apache2/minievent.evample.com/supervisor-err.log
redirect_stderr=true
stdout_logfile=/var/log/apache2/minievent.evample.com/supervisor.log
directory=/var/www/minievent.evample.com/
command=/var/www/minievent.evample.com/env/bin/python server/server.py
```

Then run `supervisorctl reload` to load the new job, you can see whether it's running
with `supervisor status`.

### Apache

This step is what makes the app accessible from outside the server machine.
To ensure everything is secured, we'll use `certbot` to generate certificates.

Create a new site on apache as `/etc/apache2/sites-available/minievent.evample.com.conf`:

```
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
certbot --authenticator webroot --installer apache certonly -w /var/www/minievent.example.com --domains minievent.example.com
```
