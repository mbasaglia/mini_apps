Mini Events
===========

## Overview

This is a demo app, it shows an interface that allows users to mark events they plan to attend.

## Configuration

```json
{
    "apps": {
        "mini_event": {
            "class": "mini_apps.apps.mini_event.MiniEventApp",
            "bot-token": "(your bot token)",
            "short-name": "events",
            "media-url": "https://miniapps.example.com/media/",
            "url": "https://miniapps.example.com/mini_event/"
        }
    }
}
```

`media-url` is the URL that serves images for the events.
`short-name` is the short name of the app on BotFather.


## Permissions

The media directory in the client needs to be writable by the web server. If you are running apache as per
[advanced installation](../installation/advanced.md), you'll need to adjust permissions:

```bash
chgrp www-data /opt/miniapps.example.com/client/media/
chmod g+w /opt/miniapps.example.com/client/media/
```


## Bot Setup

On [BotFather](https://t.me/BotFather), you'll need the following:

The menu button (`/mybots` > _@YourBotUsername_ > _Bot Settings_ > _Menu Button_), setting to the URL
to where you expose the mini events app (same as `url` in the settings json).

The app (`/newapp`), for "web app URL" use the URL as before, `events` as short name (or the value you have for `short-name`).

And enable inline mode (`/setinline`).

## Scripts


### `src/mini_apps/apps/mini_event/add_event.py`

```{argparse}
   :filename: ../src/mini_apps/apps/mini_event/add_event.py
   :func: parser
   :prog: add_event.py
```


## Admin Interface

If you created admin users (with `src/make_admin.py`), when those users
access the mini app, they will see additional options, which allows them to manage
the events.


## Limitations

The events app is a technical demo, for a fully functional app some changes are needed.

For one, the events are only specified as a time (not a date), this allows the bot
to always show some data regardless of the current date.

The bot will send notifications based on the server time, which might be different from the time shown to the users.


## Live Instance

You can access a live instance of this bot at [@GlaxMiniEventBot](https://t.me/GlaxMiniEventBot).

The live database might get wiped and recreated periodically so some data might be deleted.
