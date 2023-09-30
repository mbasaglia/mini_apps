Advanced Installation
=====================

This page shows the steps to install the mini apps directly, without using docker.

This assumes you have followed the initial installation steps as from
the [installation page](./index.md).

## System Dependencies

```bash
apt install -y python3 python3-virtualenv supervisor apache2
```

## Python Dependencies

Set up a virtual environment and install dependencies:

```
cd /var/www/minievent.example.com
virtualenv env
pip install -r server/requirements
```

## Supervisor

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


## Front-End (Apache)

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
a2enmod proxy
a2enmod proxy_http
a2ensite minievent.evample.com
apache2ctl restart
```

Follow the installation instructions for `certbot` at <https://certbot.eff.org/instructions?ws=apache&os=ubuntufocal>

To generate the certificates you can use the following command:

```bash
certbot --authenticator webroot --installer apache certonly -w /var/www/miniapps.example.com --domains miniapps.example.com
```
