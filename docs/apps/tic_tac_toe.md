Tic Tac Toe
===========

## Overview

This app allows you to play tic tac toe (also known as naughts and crosses) against another player on Telegram

## Configuration

```json
{
    "apps": {
        "tic_tac_toe": {
            "class": "mini_apps.apps.tic_tac_toe.TicTacToe",
            "bot-token": "(your bot token)",
            "short-name": "tic_tac_toe",
            "url": "https://miniapps.example.com/tic_tac_toe/"
        }
    }
}
```

## Bot Setup

On [BotFather](https://t.me/BotFather), you'll need the following:

The menu button (`/mybots` > _@YourBotUsername_ > _Bot Settings_ > _Menu Button_), setting to the URL
to where you expose the mini events app (same as `url` in the settings json).

The app (`/newapp`), for "web app URL" use the URL as before, `tic_tac_toe` as short name (or the value you have for `short-name`).

And enable inline mode (`/setinline`).


## Live Instance

You can access a live instance of this bot at [@GlaxTicTacToeBot](https://t.me/GlaxTicTacToeBot).
