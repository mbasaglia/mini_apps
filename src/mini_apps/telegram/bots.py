"""
Various bot components and utilities
"""
import math
import random
import asyncio
import pathlib
import dataclasses

from .bot import TelegramBot, ChatActionsBot
from .command import BotCommand, admin_command
from .utils import (
    MessageFormatter, static_sticker_file, mentions_from_message, user_name, send_sticker, parse_text,
    set_admin_title, InlineKeyboard
)
from .events import NewMessageEvent, CallbackQueryEvent
from . import tl

from telethon.errors.rpcerrorlist import ChatAdminRequiredError, ChatAdminInviteRequiredError, ChatIdInvalidError


class AdminMessageBot(TelegramBot):
    """
    Bot that shows a message on /admin @admin or !admin
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.admin_message = self.settings["admin-message"]
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

    async def admin(self, args: str, event: NewMessageEvent):
        """
        Notifies all admins
        """
        await event.reply(self.admin_message)

    async def on_telegram_message(self, event: NewMessageEvent):
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

    @classmethod
    def from_settings(cls, value):
        if isinstance(value, dict):
            return BotChat(value["id"], value.get("name", "?"), True)
        elif isinstance(value, int):
            return BotChat(value, "?", True)
        elif isinstance(value, str):
            return BotChat(int(value), "?", True)
        else:
            raise TypeError("Invalid chat %r" % value)

    async def to_telegram(self, client):
        try:
            return await client.get_entity(tl.types.PeerChat(self.id))
        except (ChatIdInvalidError, ValueError):
            pass
        try:
            return await client.get_entity(tl.types.PeerChannel(self.id))
        except (ChatIdInvalidError, ValueError):
            pass
        raise Exception("Not %s a chat or channel" % self)


class ApprovedChatBot(ChatActionsBot):
    """
    Telegram bot that only listens to approved chats
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.chats = {}
        for chat in self.settings.get("chats", []):
            chat = BotChat.from_settings(chat)
            self.chats[str(chat.id)] = chat

    async def get_info(self, info: dict):
        await super().get_info(info)
        chats = await self.get_chats()
        info["chats"] = [chat.bot_chat for chat in chats]

    def is_allowed_chat(self, chat):
        str_id = str(chat.id)
        if str_id not in self.chats:
            self.chats[str_id] = BotChat(chat.id, chat.title, False)
            return False
        return self.chats[str_id].approved

    async def should_process_event(self, event: NewMessageEvent):
        chat = getattr(event, "chat", None)
        # Not sure if this can actually happen
        if not chat:
            return True
        return event.bot_user.is_admin or isinstance(chat, tl.types.User) or self.is_allowed_chat(chat)

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
    async def add_chat(self, args: str, event: NewMessageEvent):
        """
        Adds the current chat to the bot
        """
        chat = await event.get_chat()
        if self.do_add_chat(chat):
            await self.admin_log("Chat %s added" % self.format_chat(chat))
        else:
            await self.admin_log("Chat %s was already enabled" % self.format_chat(chat))

    @admin_command()
    async def remove_chat(self, args: str, event: NewMessageEvent):
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
            tg_chat = await chat.to_telegram(self.telegram)
            chat.name = tg_chat.title
            tg_chat.bot_chat = chat
            chats.append(tg_chat)
        return chats

    async def do_list_chats(self, event: NewMessageEvent):
        """
        Shows allowed groups
        """
        if not event.bot_user.is_admin:
            return

        groups = self.chats.values()

        reply = "Chats this bot operates in:\n\n"
        for group in groups:
            try:
                chat = await group.to_telegram(group.telegram_id)
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

            if group.telegram_id == getattr(getattr(self, "admin_chat_bot", None), "id", None):
                reply += " Admin"

            if not found:
                reply += " (not found)"

            reply += "\n"

        await self.admin_log(reply)

    @admin_command()
    async def list_chats(self, args: str, event: NewMessageEvent):
        """
        Shows chats enabled for the bot
        """
        await self.do_list_chats(event)


class WelcomeBot(ChatActionsBot):
    """
    Bot that shows a welcome image
    """
    _asset_root = pathlib.Path()
    emoji_finder = None

    def __init__(self, settings):
        super().__init__(settings)
        self.welcome_image = None
        self.welcome_on_join = True

    async def on_user_join(self, user, chat, event):
        await super().on_user_join(user, chat, event)
        if self.welcome_on_join:
            await self.welcome(user, chat, event)

    async def welcome(self, user, chat, event):
        import lottie
        from lottie.utils.font import FontStyle, TextJustify

        full_name = user_name(user)

        anim = lottie.objects.Animation()
        fill_color = lottie.utils.color.from_uint8(0x00, 0x33, 0x99)
        stroke_color = lottie.utils.color.from_uint8(0xff, 0xcc, 0x00)
        stroke_width = 12

        font = FontStyle("Ubuntu:style=bold", 80, TextJustify.Center, emoji_finder=self.emoji_finder)
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
            self.welcome_image = self._asset_root / self.settings["welcome-image"]
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
        if self.settings["admin-chat"]:
            self.admin_chat_bot = BotChat.from_settings(self.settings["admin-chat"])
        else:
            self.admin_chat_bot = None
        self._admin_chat = None

    async def get_info(self, info: dict):
        await super().get_info(info)
        chat = await self.admin_chat()
        info["admin_chat"] = BotChat(chat.id, chat.title, True) if chat else None

    async def admin_chat(self):
        if self._admin_chat is None:
            if self.admin_chat_bot is None:
                self._admin_chat = None
            else:
                chat = await self.admin_chat_bot.to_telegram(self.telegram)
                self._admin_chat = chat
        return self._admin_chat

    async def send_to_admin_chat(self, *args, **kwargs):
        chat = await self.admin_chat()
        return await self.telegram.send_message(chat, *args, **kwargs)

    async def admin_log(self, message, *args, **kwargs):
        await self.send_to_admin_chat(message, *args, **kwargs)

    async def on_telegram_connected(self):
        await super().on_telegram_connected()

        if self.admin_chat_bot is None:
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
        self.owner = self.settings["admins"][0]

    async def get_user_info(self, id):
        user = await self.telegram(tl.functions.users.GetFullUserRequest(int(id)))
        user = user.users[0]
        return {"id": user.id, "name": user_name(user)}

    async def get_info(self, info: dict):
        await super().get_info(info)
        info.update(
            admins=await asyncio.gather(*map(self.get_user_info, self.filter.admins)),
            owner=await self.get_user_info(self.owner),
        )

    def is_admin(self, event: NewMessageEvent):
        """
        Checks if the event was triggered by an admin
        """
        user = event.bot_user
        return user and user.is_admin

    @admin_command()
    async def admin_help(self, args: str, event: NewMessageEvent):
        """
        Shows all the admin commands
        """
        await self.do_show_hidden_commands(event)

    @admin_command()
    async def mute(self, args: str, event: NewMessageEvent):
        """
        Mutes users
        """
        ids = await mentions_from_message(event)
        await self.toggle_mute(event, ids, True)

    @admin_command()
    async def unmute(self, args: str, event: NewMessageEvent):
        """
        Unmutes users
        """
        ids = await mentions_from_message(event)
        await self.toggle_mute(event, ids, False)

    @admin_command()
    async def naughty_list(self, args: str, event: NewMessageEvent):
        """
        Santa will take note
        """
        msg = MessageFormatter()

        chats = await self.get_chats()
        for chat in chats:
            msg += "%s\n" % chat.title
            naughty = []

            kicked_users = await event.client.get_participants(chat, filter=tl.types.ChannelParticipantsKicked)
            for user in kicked_users:
                naughty.append((user, "Kicked"))

            not_banned = await event.client.get_participants(chat)
            not_banned_id = set(u.id for u in not_banned)
            banned_users = await event.client.get_participants(chat, filter=tl.types.ChannelParticipantsBanned)
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
    async def set_title(self, args: str, event: NewMessageEvent):
        """
        Sets admin title for a user
        """
        chunks = await parse_text(event)

        for index, chunk in enumerate(chunks):
            if chunk.is_mention:
                if index+1 >= len(chunks) or not chunks[index+1].is_text:
                    await self.send_to_admin_chat("Missing title")
                    return

                await chunk.load()
                break
        else:
            await self.send_to_admin_chat("Missing mention")
            return

        title = chunks[index+1].text.strip()

        chats = await self.get_chats()

        reply = "Setting title for %s to %s\n" % (chunk.mentioned_name, title)
        for chat in chats:
            try:
                await set_admin_title(event.client, chat, chunk.mentioned_user, title)
                reply += "✅ %s\n" % chat.title
            except ChatAdminRequiredError:
                reply += "❌ %s - I'm not and admin\n" % chat.title
            except ChatAdminInviteRequiredError:
                reply += "❌ %s - User is already an admin or not in the chat\n" % chat.title
            except Exception as e:
                reply += "❌ %s - %s\n" % (chat.title, e)
                self.log_exception()

        await self.send_to_admin_chat(reply)

    async def do_show_hidden_commands(self, event: NewMessageEvent):
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
                except Exception:
                    self.log_exception()

        if not reply:
            reply = "Nothing to do"
        await self.send_to_admin_chat(reply)

    @admin_command()
    async def chat_info(self, args: str, event: NewMessageEvent):
        """
        Shows chat ID and title
        """
        chat = await event.get_chat()
        msg = "Title: %s\nId: %s" % (chat.title, chat.id)
        if not self.admin_chat_bot:
            await self.telegram.send_message(event.chat, msg)
        else:
            await self.send_to_admin_chat(msg)

    @admin_command()
    async def user_info(self, args: str, event: NewMessageEvent):
        """
        Shows user ID and and name
        """
        users = await mentions_from_message(event)
        if users:
            await self.send_to_admin_chat("\n".join("%s %s" % item for item in users.items()))
        else:
            await self.send_to_admin_chat("No users to get info for")


class RandomChoiceCaptchaBot(ChatActionsBot):
    """
    Shows a captcha based on settings
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.values = list(self.settings["values"].items())
        self.choices = self.settings.get("choices", 6)
        self.prompt = self.settings.get(
            "prompt",
            "Hi [{user_name}](tg://user?id={user.id}) welcome to **{chat.title}**.\nPlease click the button showing {correct}"
        )
        self.challenges = {}
        self.columns = math.ceil(math.sqrt(self.choices))
        self.timeout = self.settings.get("timeout", 5)

    async def on_user_join(self, user, chat, event):
        options = random.choices(self.values, k=self.choices)
        correct = options[0]
        incorrect = options[1:]
        random.shuffle(options)
        message = self.prompt.format(
            user=user,
            chat=chat,
            user_name=user_name(user),
            correct=correct,
            incorrect=incorrect,
            timeout=self.timeout
        )
        buttons = InlineKeyboard()
        for i, (display, value) in enumerate(options):
            if i % self.columns == 0:
                buttons.add_row()
            buttons.add_button_callback(display, "%s::%s" % (user.id, value))

        buttons.add_row()
        buttons.add_button_callback("🟩 Approve", "admin:approve:%s" % user.id)
        buttons.add_button_callback("🟥 Reject", "admin:reject:%s" % user.id)

        self.challenges[user.id] = correct[1]

        await self.telegram.edit_permissions(chat, user, send_messages=False)
        await self.telegram.send_message(chat, message, parse_mode="md")

        await asyncio.sleep(self.timeout * 60)
        challenge = self.challenges.pop(user.id, None)
        if challenge is not None:
            msg = MessageFormatter()
            msg += "User "
            msg.mention(user_name(user), user.id)
            msg += " "
            msg.bold("TIMED OUT")
            msg += " (%s minutes)" % self.timeout
            await self.admin_log(msg.text, formatting_entities=msg.entities)
            await self.telegram.edit_permissions(event.chat, user, view_messages=False)

    async def on_telegram_callback(self, event: CallbackQueryEvent):
        button_user_id, button_action, button_value = event.query.split(":", 2)

        if button_user_id == "admin":
            user_id = int(button_value)
            user = await self.telegram.get_entity(tl.types.PeerUser(user_id))

            challenge = self.challenges.pop(user.id, None)
            if not challenge:
                self.admin_log("Captcha challenge not found")
                await event.answer()
                return

            msg = MessageFormatter()
            msg += "User "
            msg.mention(user_name(user), user.id)
            msg += " "
            if button_action == "approve":
                msg.bold("APPROVED")
                await self.telegram.edit_permissions(event.chat, user, send_messages=True)
            else:
                msg.bold("REJECTED")
                await self.telegram.edit_permissions(event.chat, user, view_messages=False)

            admin = await event.get_sender()
            msg += " by "
            msg.mention(user_name(admin), admin.id)
            await event.answer()
            return

        button_user_id = int(button_user_id)
        user = await event.get_sender()
        if button_user_id != user.id:
            await event.answer()
            return

        challenge = self.challenges.pop(user.id, None)
        if not challenge:
            await event.answer()
            return

        msg = MessageFormatter()
        msg += "User "
        msg.mention(user_name(user), user.id)
        msg += " "

        if challenge == event.query:
            msg.bold("PASSED")
            await self.telegram.edit_permissions(event.chat, user, send_messages=True)
        else:
            msg.bold("FAILED")
            await self.telegram.edit_permissions(event.chat, user, view_messages=False)

        msg += " the captcha!"
        await self.admin_log(msg.text, formatting_entities=msg.entities)
        message = await event.get_message()
        await message.delete()
        await event.answer()


class ReplyBot(TelegramBot):
    """
    Bot that gives fixed (or randomized) replies to given commands
    """
    class Command:
        def __init__(self, messages, kwargs):
            self.kwargs = kwargs
            self.messages = messages

        async def __call__(self, bot, args, event):
                await event.client.send_message(event.chat, random.choice(self.messages), **self.kwargs)

    def __init__(self, settings):
        super().__init__(settings)
        for trigger, command in settings["commands"].items():
            kwargs = {}
            if isinstance(command, dict):
                kwargs = command
                command = kwargs.pop("message")

            description = kwargs.pop("description", "")
            hidden = kwargs.pop("hidden", False)
            admin_only = kwargs.pop("admin_only", False)

            if not isinstance(command, list):
                command = [command]

            handler = self.Command(command, kwargs)
            self.bot_commands[trigger] = BotCommand(handler, trigger, description, hidden, admin_only)
