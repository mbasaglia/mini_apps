Web Socket Protocol
===================

The Mini Apps have a front-end page that communicates with the bot via websockets.

The communication is done by sending small JSON-encoded messages though the socket, this page describes their structure.

## Basics

All messages have a `type` attribute that determintes the kind of message.

Messages from the client must also have an `app` attribute to identify which app the message is delivered to.

## Connection-related messages

These messages are common to all the apps, and they are used to establish the connection.

### `connect`

Sent by the server as soon a client connects, notifying the server can accept messages from that client.


### `login`

Sent by the client, including the telegam mini app authentication (taken from `window.Telegram.WebApp.initData`).

### `disconnect`

Sent by the server if the `login` failed, the server will no longer accept messages from this client.

### `welcome`

Sent by the server if the `login` succeeded, this includes the user data:

Example:

```json
{
    "type": "welcome",
    "telegram_id": 12345,
    "name": "Test",
    "is_admin": false
}
```

## Mini Events

This section describes messages specific to the Mini Events app.

### `event`

Sent by the server when there is a new event available or an existing event has been modified.

It's also sent after welcome to give all the existing events.

This includes all the event-specific data.

Example:

```json
{
    "type": "event",
    "id": 1,
    "title": "Title",
    "description": "Description",
    "image": "https://miniapps.example.com/media/image.jpg",
    "start": "12:00",
    "duration": 1,
    "attending": false,
    "attendees": 3
}
```

### `events-loaded`

This is sent during the initial connection, after all the `event` messages have been sent.

### `attend`

Sent by the client to register attendance to an event, it includes the property `event` with the corresponding ID.

### `leave`

Sent by the client to cancel attendance to an event, same format as `attend`.


