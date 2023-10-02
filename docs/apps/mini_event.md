Mini Events
===========

## Overview

This is a demo app, it shows an interface that allows users to mark events they plan to attend.

The events

## Configuration

```json
{
    "apps": {
        "mini_event": {
            "class": "mini_apps.apps.mini_event.MiniEventApp",
            "bot-token": "(your bot token)",
            "media-url": "https://miniapps.example.com/media/",
            "url": "https://miniapps.example.com/mini_event/"
        }
    }
}
```

## Bot Setup

On [BotFather](https://t.me/BotFather), you'll need the following:

The menu button (`/mybots` > _@YourBotUsername_ > _Bot Settings_ > _Menu Button_), setting to the URL
to where you expose the mini events app (same as `url` in the settings json).

The app (`/newapp`), for "web app URL" use the URL as before, `events` as short name.

And enable inline mode (`/setinline`).

## Admin Interface

If you created admin users (with `server/make_admin.py`), when those users
access the mini app, they will see additional options, which allows them to manage
the events.


## Limitations

The events app is a technical demo, for a fully functional app some changes are needed.

For one, the events are only specified as a time (not a date), this allows the bot
to always show events without having to set up many events throughout the course
of several days.

For the live instance, the bot will send notifications based on the server time.
The live database might get wiped and recreated periodically so some data will be deleted.


