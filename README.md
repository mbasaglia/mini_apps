Event Telegram Mini-App Demo
============================

This is a demo of telegram mini apps.

It shows a list of events the user can attend and uses websockets to dynamically
update information to the client.


Set Up
------

See the [installation page](./docs/installation/index.md) for the installation and
setup guide.


Mini Apps
---------

The installation guide above shows the configuration for the "Mini Events" app, which serves as a demo for the system.

You can find detailed description, configuration options, and limitations of all the availble apps in the [Available Apps](./docs/apps.md) page.

To make your own mini app, see [Making Your Own App](./docs/custom-app.md) page.


Initial Data
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

If you want to run these on the docker instance, they should be invoked like this:

```bash
docker exec -ti mini_apps_miniapp_1  server/list_users.py
```

If you want to run them directly, you need to ensure you have Python
and the pip requirements from `server/requirements.txt` installed.

Please note that this demo uses SQLite to minimize set up, you might need to restart the server after changing data
from the database.


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


License
-------

GPLv3+ https://www.gnu.org/licenses/gpl-3.0.en.html
