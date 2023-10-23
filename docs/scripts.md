Management Scripts
==================

There are several server-side scripts that allow you to manage the app and add initial data.

All these scripts support the `--help` command that gives more details on how they work.

The paths mentioned here are relative to the project root (`/opt/miniapps.example.com` on the [installation guide](./installation/basic.md)).

If you want to run these on the docker instance, they should be invoked like this:

```bash
docker-compose exec miniapp src/list_users.py
```

If you want to run them directly, you need to ensure you have Python
and the pip requirements from `src/requirements.txt` installed.

Please note that the installation guide uses SQLite to minimize set up,
so you might need to restart the server after changing data on the database.


## `src/list_users.py`

```{argparse}
   :filename: ../src/list_users.py
   :func: parser
   :prog: src/list_users.py
```

## `src/make_admin.py`

```{argparse}
   :filename: ../src/make_admin.py
   :func: parser
   :prog: src/make_admin.py
```

## `src/server.py`

```{argparse}
   :filename: ../src/server.py
   :func: parser
   :prog: src/server.py
```

## `src/websocket_client.py`

```{argparse}
   :filename: ../src/websocket_client.py
   :func: parser
   :prog: src/websocket_client.py
```
