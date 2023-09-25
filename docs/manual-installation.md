Manual Installation
-------------------

This page shows the steps to install the back-end directly, without using docker.

This assumes you have followed the other installation steps as from the main Readme.

## System Dependencies

```bash
apt install -y python3 python3-virtualenv supervisor
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
