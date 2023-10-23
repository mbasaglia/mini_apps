Advanced Installation
=====================

This page shows the steps to install the mini apps directly, without using docker.

This assumes you have followed the initial installation steps from the [basic installation page](./basic.md).

## System Dependencies

```bash
apt install -y python3 python3-virtualenv supervisor apache2
```

## Python Dependencies

Set up a virtual environment and install dependencies:

```
cd /opt/miniapps.example.com
virtualenv --prompt "(miniapps) " env
. env/bin/activate
pip install -r src/requirements.txt
```

## Supervisor

Supervisor is a tool that allows you to keep running scripts in the background,
and it provides commands to start and stop them. Here we use it to run the
python script that manages the server-side web socket.

The supervisor config will be in `/etc/supervisor/conf.d/miniapps.conf`
with the following content:

```
[program:miniapps]
user=www-data
group=www-data
stderr_logfile=/var/log/apache2/miniapps.example.com/supervisor-err.log
redirect_stderr=true
stdout_logfile=/var/log/apache2/miniapps.example.com/supervisor.log
directory=/opt/miniapps.example.com/
command=/opt/miniapps.example.com/env/bin/python src/server.py
```

Then run `supervisorctl reload` to load the new job, you can see whether it's running
with `supervisor status`.


## Front-End (Apache)

This step is what makes the app accessible from outside the server machine.

You will have to ensure apache has read access to the `client` directory, if `/opt/miniapps.example.com` doesn't work,
you can move over client-side files to something like `/var/www/miniapps.example.com` and change the apache config accordingly.

To ensure everything is secured, we'll use `certbot` to generate certificates.

Create a new site on apache as `/etc/apache2/sites-available/miniapps.example.com.conf`:

```apache
# This sets up the SSL (encrypted) virtual host, which actually hosts the website
<VirtualHost *:443>
    # Basic Setup (domain and directory)
    ServerName miniapps.example.com
    DocumentRoot /opt/miniapps.example.com/client

    # Makes the local websocket available as wss://miniapps.example.com/wss/
    ProxyRequests Off
    ProxyPass /wss/ ws://localhost:2536

    # SSL settings
    SSLEngine on
    SSLCertificateFile      /etc/letsencrypt/live/miniapps.example.com/cert.pem
    SSLCertificateKeyFile   /etc/letsencrypt/live/miniapps.example.com/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/miniapps.example.com/chain.pem
    Header always set Strict-Transport-Security "max-age=2678400"
</VirtualHost>

# This is the non-encrypted virtual host, which redirects all requests from http to https
# only giving access to the certbot
<VirtualHost *:80>
    ServerName miniapps.example.com

    <Location ~ "^(?!/.well-known)">
        Redirect permanent / "https://miniapps.example.com/"
    </Location>

    Alias "/.well-known" "/opt/miniapps.example.com/.well-known"
    <Directory /opt/miniapps.example.com/.well-known>
        Allow from all
        Options -Indexes
    </Directory>
</VirtualHost>
```

The above assumes you set up SSL certificates with [certbot](https://certbot.eff.org/instructions).

Here is an example `certbot` invocation:

```bash
certbot --authenticator webroot --installer apache certonly -w /opt/miniapps.example.com --domains miniapps.example.com
```


Enable the new site and restart Apache

```bash
a2enmod proxy
a2enmod proxy_http
a2ensite miniapps.example.com
apache2ctl restart
```
