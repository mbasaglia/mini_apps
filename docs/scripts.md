Management Scripts
==================

There are several server-side scripts that allow you to manage the app and add initial data.

All these scripts support the `--help` command that gives more details on how they work.

The paths mentioned here are relative to the project root (`/opt/miniapps.example.com` on the [installation guide](./basic.md)).

If you want to run these on the docker instance, they should be invoked like this:

```bash
docker-compose exec miniapp server/list_users.py
```

If you want to run them directly, you need to ensure you have Python
and the pip requirements from `server/requirements.txt` installed.

Please note that the installation guide uses SQLite to minimize set up,
so you might need to restart the server after changing data on the database.


## `server/add_event.py`

```{argparse}
   :filename: ../server/add_event.py
   :func: parser
   :prog: server/add_event.py
```

## `server/list_users.py`

```{argparse}
   :filename: ../server/list_users.py
   :func: parser
   :prog: server/list_users.py
```

## `server/make_admin.py`

```{argparse}
   :filename: ../server/make_admin.py
   :func: parser
   :prog: server/make_admin.py
```

## `server/server.py`

```{argparse}
   :filename: ../server/server.py
   :func: parser
   :prog: server/server.py
```

## `server/websocket_client.py`

```{argparse}
   :filename: ../server/websocket_client.py
   :func: parser
   :prog: server/websocket_client.py
```
