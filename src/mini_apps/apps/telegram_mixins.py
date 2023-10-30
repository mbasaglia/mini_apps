"""
Various bot components and utilities
"""
import pathlib
import dataclasses

from ..telegram import TelegramBot, ChatActionsBot, bot_command
from ..command import BotCommand, admin_command
from ..utils.telegram import (
    MessageFormatter, static_sticker_file, mentions_from_message, user_name, send_sticker
)

from telethon import tl
from telethon.events import NewMessage
from telethon.errors.rpcerrorlist import ChatAdminRequiredError, ChatAdminInviteRequiredError

import lottie
from lottie.utils.font import FontStyle, TextJustify




class AdminMessageBot(TelegramBot):
    """
    Bot that shows a message on /admin @admin or !admin
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.admin_message = self.settings.admin_message
        self.trigger = settings.get("trigger", "admin")

    def get_bot_commands(self):
        commands = super().get_bot_commands()
        commands[self.trigger] = BotCommand.from_function(AdminMessageBot.admin, self.trigger, None)
        return commands

    async def get_info(self, info: dict):
        await super().get_info(info)
        info.update(
            admin_message=self.admin_message
        )

    async def admin(self, args: str, event: NewMessage.Event):
        """
        Notifies all admins
        """
        await event.reply(self.admin_message)

    async def on_telegram_message(self, event: NewMessage.Event):
        if await super().on_telegram_message(event):
            return True

        if event.text.startswith("@" + self.trigger) or event.text.startswith("!" + self.trigger):
            await self.admin(event.text[len(self.trigger)+1:], event)
            return True

        return False


@dataclasses.dataclass
class BotChat:
    id: int
    name: str
    approved: bool = False


class ApprovedChatBot(ChatActionsBot):
    """
    Telegram bot that only listens to approved chats
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.chats = {}

    async def get_info(self, info: dict):
        await super().get_info(info)
        chats = await self.get_chats()
        info.update(
            chats=[chat.bot_chat for chat in chats]
        )

    def is_allowed_chat(self, chat):
        str_id = str(chat.id)
        if str_id not in self.chats:
            self.chats[str_id] = BotChat(chat.id, chat.title, False)
            return False
        return self.chats[str_id].approved

    async def should_process_event(self, event: NewMessage.Event):
        chat = getattr(event, "chat", None)
        # Not sure if this can actually happen
        if not chat:
            return True
        return self.is_allowed_chat(chat) or event.bot_user.is_admin or isinstance(chat, tl.types.User)

    async def on_self_join(self, chat, event):
        self.chats[str(chat.id)] = BotChat(chat.id, chat.title)

    async def on_self_leave(self, chat, event):
        self.chats.pop(str(chat.id))

    def do_add_chat(self, chat):
        chat_id = str(chat.id)
        chat = BotChat(chat.id, chat.title, True)
        self.chats[chat_id] = chat
        return chat

    def do_remove_chat(self, chat):
        chat_id = str(chat.id)
        return self.chats.pop(chat_id, None)

    def format_chat(self, chat):
        return "%s %r" % (chat.id, chat.title)

    @admin_command()
    async def add_chat(self, args: str, event: NewMessage.Event):
        """
        Adds the current chat to the bot
        """
        chat = await event.get_chat()
        if self.do_add_chat(chat):
            await self.admin_log("Chat %s added" % self.format_chat(chat))
        else:
            await self.admin_log("Chat %s was already enabled" % self.format_chat(chat))

    @admin_command()
    async def remove_chat(self, args: str, event: NewMessage.Event):
        """
        Removes the current chat from the bot
        """
        chat = await event.get_chat()
        if self.do_remove_chat(chat):
            await self.admin_log("Chat %s removed" % self.format_chat(chat))
        else:
            await self.admin_log("Chat %s wasn't enabled" % self.format_chat(chat))

    async def get_chats(self):
        chats = []
        for chat in self.chats.values():
            tg_chat = await self.telegram.get_entity(tl.types.PeerChat(int(chat.id)))
            chat.name = tg_chat.title
            tg_chat.bot_chat = chat
            chats.append(tg_chat)
        return chats

    async def do_list_chats(self, event: NewMessage.Event):
        """
        Shows allowed groups
        """
        if not event.bot_user.is_admin:
            return

        groups = self.chats.values()

        reply = "Chats this bot operates in:\n\n"
        for group in groups:
            try:
                chat = await event.client.get_entity(tl.types.PeerChat(int(group.telegram_id)))
                name = chat.title
                found = True
            except Exception:
                name = group.name
                found = False

            reply += "(%s) %s -" % (group.id, name)

            if group.approved:
                reply += " Approved"
            else:
                reply += " Needs Approval"

            if group.telegram_id == self.admin_chat_id:
                reply += " Admin"

            if not found:
                reply += " (not found)"

            reply += "\n"

        await self.send_to_admin_chat(reply)

    @admin_command()
    async def list_chats(self, args: str, event: NewMessage.Event):
        """
        Shows chats enabled for the bot
        """
        await self.do_list_chats(event)


class WelcomeBot(ChatActionsBot):
    """
    Bot that shows a welcome image
    """
    _asset_root = pathlib.Path()
    emoji_path = pathlib.Path()

    def __init__(self, settings):
        super().__init__(settings)
        self.welcome_image = None

    async def on_user_join(self, user, chat, event):
        await self.welcome(user, chat, event)

    async def welcome(self, user, chat, event):
        full_name = user_name(user)

        anim = lottie.objects.Animation()
        fill_color = lottie.utils.color.from_uint8(0x00, 0x33, 0x99)
        stroke_color = lottie.utils.color.from_uint8(0xff, 0xcc, 0x00)
        stroke_width = 12

        font = FontStyle("Ubuntu:style=bold", 80, TextJustify.Center, emoji_svg=self.emoji_path)
        text_layer = lottie.objects.ShapeLayer()
        anim.add_layer(text_layer)
        group = font.render("Welcome", lottie.NVector(256, font.line_height))
        text_layer.add_shape(group)
        text_layer.add_shape(lottie.objects.Fill(fill_color))
        text_layer.add_shape(lottie.objects.Stroke(stroke_color, stroke_width))

        pos = lottie.NVector(256, 512)
        group = font.render(full_name, pos)
        group.transform.anchor_point.value = pos.clone()
        group.transform.position.value = pos.clone()
        bbox = group.bounding_box()
        max_width = 512 - 16
        if bbox.width > max_width:
            group.transform.scale.value *= max_width / bbox.width
            bbox = group.bounding_box()
        group.transform.position.value.y -= bbox.y2 - 512 + 32
        text_layer.add_shape(group)
        text_layer.add_shape(lottie.objects.Fill(stroke_color))
        text_layer.add_shape(lottie.objects.Stroke(stroke_color, stroke_width))

        if self.welcome_image is None:
            self.welcome_image = self._asset_root / self.settings.welcome_image
        asset = lottie.objects.Image.embedded(self.welcome_image)
        anim.assets.append(asset)
        anim.add_layer(lottie.objects.ImageLayer(asset.id))

        await send_sticker(event.client, event.chat, static_sticker_file(anim))


class LogToChatBot(TelegramBot):
    """
    Bot that logs info in a chat
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.admin_chat_id = self.settings.admin_chat_id
        self._admin_chat = None

    async def get_info(self, info: dict):
        await super().get_info(info)
        chat = await self.admin_chat()
        info["admin_chat"] = BotChat(chat.id, chat.title, True)

    async def admin_chat(self):
        if self._admin_chat is None:
            self._admin_chat = await self.telegram.get_entity(tl.types.PeerChat(int(self.admin_chat_id)))
        return self._admin_chat

    async def send_to_admin_chat(self, *args, **kwargs):
        chat = await self.admin_chat()
        return await self.telegram.send_message(chat, *args, **kwargs)

    async def admin_log(self, message):
        await self.send_to_admin_chat(message)

    async def on_telegram_connected(self):
        await super().on_telegram_connected()

        if self.admin_chat_id is None:
            return

        chat = await self.admin_chat()
        input = await self.telegram.get_input_entity(chat)
        scope = tl.types.BotCommandScopePeer(input)
        await self.send_telegram_commands(scope, lambda cmd: cmd.admin_only)


class AdminCommandsBot(LogToChatBot, ApprovedChatBot):
    """
    Bot with admin helper function
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.owner = self.settings.admins[0]

    async def get_info(self, info: dict):
        await super().get_info(info)
        info.update(
            admins=self.filter.admins,
            owner=self.owner,
        )

    def is_admin(self, event: NewMessage.Event):
        """
        Checks if the event was triggered by an admin
        """
        user = event.bot_user
        return user and user.is_admin

    @admin_command()
    async def admin_help(self, args: str, event: NewMessage.Event):
        """
        Shows all the admin commands
        """
        await self.do_show_hidden_commands(event)

    @admin_command()
    async def mute(self, args: str, event: NewMessage.Event):
        """
        Mutes users
        """
        ids = await mentions_from_message(event)
        await self.toggle_mute(event, ids, True)

    @admin_command()
    async def unmute(self, args: str, event: NewMessage.Event):
        """
        Unmutes users
        """
        ids = await mentions_from_message(event)
        await self.toggle_mute(event, ids, False)

    @admin_command()
    async def naughty_list(self, args: str, event: NewMessage.Event):
        """
        Santa will take note
        """
        from telethon.tl.types import ChannelParticipantsKicked, ChannelParticipantsBanned

        msg = MessageFormatter()

        chats = await self.get_chats()
        for chat in chats:
            msg += "%s\n" % chat.title
            naughty = []

            kicked_users = await event.client.get_participants(chat, filter=ChannelParticipantsKicked)
            for user in kicked_users:
                naughty.append((user, "Kicked"))

            not_banned = await event.client.get_participants(chat)
            not_banned_id = set(u.id for u in not_banned)
            banned_users = await event.client.get_participants(chat, filter=ChannelParticipantsBanned)
            for user in banned_users:
                naughty.append((user, "Restricted" if user.id in not_banned_id else "Banned"))

            for user, reason in naughty:
                msg += " - "
                name = ""
                if user.username:
                    name += "@" + user.username
                else:
                    name += user_name(user)
                inuser = await event.client.get_input_entity(user)
                msg.mention(name, inuser)
                msg += " : "
                msg.bold(reason)
                msg += "\n"

            if not banned_users and not kicked_users:
                msg += " (No one)\n"

            msg += "\n"

        await self.send_to_admin_chat(msg.text or "Everyone is nice", formatting_entities=msg.entities)

    @admin_command()
    async def set_title(self, args: str, event: NewMessage.Event):
        """
        Sets admin title for a user
        """
        chunks = await event.parse_text()

        for index, chunk in enumerate(chunks):
            if chunk.is_mention:
                if index+1 >= len(chunks) or not chunks[index+1].is_text:
                    await self.send_to_admin_chat("Missing title")
                    return

                await chunk.load()
                id = chunk.mentioned_id
                name = chunk.mentioned_name
                break
        else:
            await self.send_to_admin_chat("Missing mention")
            return

        title = chunks[index+1].text.strip()

        chats = await self.get_chats()

        reply = ""
        for chat in chats:
            try:
                entity = await event.client.set_admin_title(chat, chunk.mentioned_name, title)
                reply += "✅ %s\n" % chat.title
            except ChatAdminRequiredError:
                reply += "❌ %s - I'm not and admin\n" % chat.title
            except ChatAdminInviteRequiredError as e:
                reply += "❌ %s - User is already an admin or not in the chat\n" % chat.title
            except Exception as e:
                reply += "❌ %s - %s\n" % (chat.title, e)

        await self.send_to_admin_chat(reply)

    async def do_show_hidden_commands(self, event: NewMessage.Event):
        """
        Shows hidden commands
        """
        if not self.is_admin(event):
            return

        reply = "Available admin commands:\n\n"

        for _, command in sorted(self.bot_commands.items()):
            if command.hidden:
                reply += "/{trigger} {description}\n".format(
                    trigger=command.trigger,
                    description=command.description
                )

        reply += "\nAdmins:\n\n"
        for id in self.filter.admins:
            try:
                user = await event.client(tl.functions.users.GetFullUserRequest(int(id)))
                reply += user_name(user.user)
            except Exception:
                reply += str(id)
            reply += "\n"

        await self.send_to_admin_chat(reply)

    async def toggle_mute(self, event, mentions, mute):
        """
        Mutes/unmutes based on mentions
        """
        chats = await self.get_chats()

        reply = ""
        action = "mute" if mute else "unmute"
        for idstr, name in mentions.items():
            id = int(idstr)
            for chat in chats:
                try:
                    await self.telegram.edit_permissions(
                        chat,
                        id,
                        send_messages=not mute,
                    )
                    reply += "%s %s in %s\n" % (name, action + "d", chat.title)
                except ChatAdminRequiredError:
                    reply += "I don't have enough permissions in %s to %s %s\n" % (chat.title, action, name)
                except Exception as e:
                    self.log_exception()

        if not reply:
            reply = "Nothing to do"
        await self.send_to_admin_chat(reply)

    @admin_command()
    async def chat_info(self, args: str, event: NewMessage.Event):
        """
        Shows chat ID and title
        """
        chat = await event.get_chat()
        msg = "Title: %s\nId: %s" % (chat.title, chat.id)
        if not self.admin_chat_id:
            await self.telegram.send_message(event.chat, msg)
        else:
            await self.send_to_admin_chat(msg)

    @admin_command()
    async def user_info(self, args: str, event: NewMessage.Event):
        """
        Shows user ID and and name
        """
        users = await mentions_from_message(event)
        if users:
            await self.send_to_admin_chat("\n".join("%s %s" % item for item in users.items()))
        else:
            await self.send_to_admin_chat("No users to get info for")
