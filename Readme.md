Event Telegram Mini-App Demo
============================

This is a demo of telegram mini apps.

It shows a list of events the user can attend and uses websockets to dynamically
update information to the client.


Installation
------------

Here are some configuration examples on how to set up this demo.
This assumes the domain is `minievent.example.com` and Apache web server,
as well as some other tools.

First check out the repository:

```bash
cd /var/www/
git clone TODO url minievent.example.com
```

Set up a virtual environment and install dependencies:

```
cd /var/www/minievent.example.com
virtualenv env
pip install -r server/requirements
```


To run the server, set up a supervisor job, add the following to
`/etc/supervisor/conf.d/minievent.conf` (taking care of using your actual bot token):

```
[program:minievent]
user=www-data
group=www-data
stderr_logfile=/var/log/apache2/minievent.example.org/supervisor-err.log
redirect_stderr=true
stdout_logfile=/var/log/apache2/minievent.example.org/supervisor.log
directory=/var/www/minievent.example.org/
command=/var/www/minievent.example.org/env/bin/python server/server.py --database /home/melano/www/minievent.example.org/server/db/db.sqlite --port 2536 --token (bot-token)
```

Set up Apache (this assumes you know how to add a new virtualhost and TLS certificates):

```
<VirtualHost *:443>
        # ...

        DocumentRoot /var/www/minievent.example.org/client

        ProxyRequests Off
        ProxyPass /wss/ ws://localhost:2536
</VirtualHost>
```

Add the settings file for the client `/var/www/minievent.example.com/client/settings.json`
with the following content:

```json
{
    "socket": "wss://minievent.example.com/wss"
}
```
