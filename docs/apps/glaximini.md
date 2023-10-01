Glaximini
=========

This is a very basic animated sticker editor.

## Configuration

```json
{
    "apps": {
        "glaximini": {
            "class": "mini_apps.apps.glaximini.app.Glaximini",
            "bot-token": "(your bot token)",
            "url": "https://miniapps.example.com/glaximini/"
        }
    }
}
```

## Bot Setup

On [BotFather](https://t.me/BotFather), you'll need the following:

The menu button (`/mybots` > _@YourBotUsername_ > _Bot Settings_ > _Menu Button_), setting to the URL
to where you expose the mini events app (same as `url` in the settings json).

The app (`/newapp`), for "web app URL" use the URL as before.

And enable inline mode (`/setinline`).

## UI

It has 3 tools: _Select_, _Rectangle_, _Ellipse_, and _Bezier_.

The _Select_ tool allows you to move and edit the shapes, just click on a shape to select it, drag a shape to move it,
or drag on the handles of the selected shape to edit its properties.

The _Rectangle_ and _Ellipse_ tools work the same way, you drag on the canvas to create the corresponding shape.

With _Bezier_ you can create more complex shapes just click on the canvas to add vertices,
if you click on the starting point the shape will be closed. You can also click and drag to make the edges more curved.

After the tools, it has _Undo_ and _Redo_ buttons, as well as a button to share the created sticker on Telegram.

On the row below, the first button will delete the selected shape, while the others will change fill and stroke.

Below the canvas you have _Play_ / _Pause_ buttons as well as the _Keyframe_ button.
Below these buttons is the timeline slider.


## Animating

To add animations to the selected shape, scroll on the timeline to the initial frame, then press the _Keyframe_ button.

This will add a keyframe at the selected time for all the properties of the selected object.

Then scroll the timeline to a different time, change some properties of the shape (for example, position or color) and
press the _Keyframe_ button again.

After that, pressing _Play_ should show your shape animating between those keyframes.


## Limitations

Currently it's limited to one animation per user, and the feature support is rather limited.
