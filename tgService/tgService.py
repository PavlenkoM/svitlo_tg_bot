import html
import logging
import asyncio
from typing import Awaitable, Callable, List, Optional
from telegram import BotCommand, BotCommandScopeChat, ForceReply, Update
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import config
from utils import styler
from storage import storageService

# Commands in the Telegram menu for everyone
PUBLIC_COMMANDS = [
    BotCommand("start", "Subscribe to electricity notifications"),
    BotCommand("stop", "Unsubscribe"),
    BotCommand("partial_on", "Also notify when only some phases have electricity"),
    BotCommand("partial_off", "Notify only ON / OFF"),
    BotCommand("phases_on", "Show phase voltages in messages"),
    BotCommand("phases_off", "Hide phase voltages in messages"),
]
# Extra commands shown only in the private chats of admins
ADMIN_COMMANDS = [
    BotCommand("status", "Current electricity status (admin)"),
]

class TgService:
    _tgApp = None
    _statusProvider: Optional[Callable[[], Awaitable[str]]] = None

    def setStatusProvider(self, provider: Callable[[], Awaitable[str]]) -> None:
        """Function that builds the /status reply (set from main to avoid a circular import)"""
        self._statusProvider = provider

    def _getAdminIds(self) -> List[int]:
        return [int(adminId) for adminId in config.get('admin-ids') or []]

    async def initBot(self, token: str) -> None:
        styler.info("Starting Telegram bot...")
        self._tgApp = Application.builder().token(token).build()

        # on different commands - answer in Telegram
        # Only new messages: edited messages have no update.message to reply to
        self._tgApp.add_handler(CommandHandler("start", self.commandStart, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("stop", self.commandStop, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("partial_on", self.commandPartialOn, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("partial_off", self.commandPartialOff, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("phases_on", self.commandPhasesOn, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("phases_off", self.commandPhasesOff, filters=filters.UpdateType.MESSAGE))
        self._tgApp.add_handler(CommandHandler("status", self.commandStatus, filters=filters.UpdateType.MESSAGE))

        # Initialize the application
        await self._tgApp.initialize()

        # Show the commands in the Telegram menu
        try:
            await self._tgApp.bot.set_my_commands(PUBLIC_COMMANDS)
        except Exception as e:
            styler.warning(f"Failed to set bot commands menu: {e}")

        # Admin menu: only in the admin's private chat (private chat id == user id)
        for adminId in self._getAdminIds():
            try:
                await self._tgApp.bot.set_my_commands(PUBLIC_COMMANDS + ADMIN_COMMANDS, scope=BotCommandScopeChat(adminId))
            except Exception as e:
                styler.warning(f"Failed to set admin commands menu for {adminId} (send /start to the bot first): {e}")
        styler.info("Telegram bot initialized.")
    
    async def startPolling(self, token) -> None:
        """Start the bot polling"""
        if not self._tgApp:
            await self.initBot(token)

        styler.info("Starting Telegram bot polling...")
        # Start the bot using the updater
        await self._tgApp.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await self._tgApp.start()
        
        try:
            # Keep the bot running
            await asyncio.Event().wait()
        finally:
            await self._tgApp.stop()
            await self._tgApp.updater.stop()
            await self._tgApp.shutdown()

    async def commandStart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Subscribe the chat to notifications when the command /start is issued."""
        styler.info("Received /start command")
        chatId = update.effective_chat.id
        user = update.effective_user

        # Store the chat ID for future messaging, or re-subscribe a chat that sent /stop before
        if storageService.get_chat_info(chatId):
            storageService.activate_chat_id(chatId)
        else:
            storageService.saveChat(chatId, user.username, user.first_name, user.last_name)

        await update.message.reply_html(
            f"Hi {html.escape(user.first_name or '')}!\n"
            "You are subscribed to electricity notifications. Send /stop to unsubscribe."
        )

    async def commandStop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Unsubscribe the chat from notifications when the command /stop is issued."""
        styler.info("Received /stop command")
        storageService.deactivate_chat_id(update.effective_chat.id)
        await update.message.reply_text("You are unsubscribed. Send /start to subscribe again.")

    async def commandPartialOn(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Turn on PARTIAL notifications for the chat"""
        await self._setChatSetting(update, "partial_on", storageService.set_show_partial, True,
            "⚠️ PARTIAL messages are ON.\n"
            "You will also get a message when only some phases have electricity. "
            "Send /partial_off to get only ON / OFF.")

    async def commandPartialOff(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Turn off PARTIAL notifications for the chat"""
        await self._setChatSetting(update, "partial_off", storageService.set_show_partial, False,
            "PARTIAL messages are OFF.\n"
            "You will get only ON / OFF. Send /partial_on to turn them on.")

    async def commandPhasesOn(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show phase voltages in notifications for the chat"""
        await self._setChatSetting(update, "phases_on", storageService.set_show_phases, True,
            "Phase voltages are shown in messages:\n"
            "🟢 230 V | 🟢 229 V | 🟢 228 V\n"
            "Send /phases_off to hide them.")

    async def commandPhasesOff(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Hide phase voltages in notifications for the chat"""
        await self._setChatSetting(update, "phases_off", storageService.set_show_phases, False,
            "Phase voltages are hidden. Messages show only the state, for example 💡 - ON.\n"
            "Send /phases_on to show them.")

    async def commandStatus(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Current electricity status. Admins only, in a private chat; others get no reply at all."""
        userId = update.effective_user.id if update.effective_user else None
        if userId not in self._getAdminIds() or update.effective_chat.type != "private":
            styler.warning(f"Ignored /status from user {userId} in chat {update.effective_chat.id}: not an admin private chat")
            return

        styler.info("Received /status command")
        if not self._statusProvider:
            await update.message.reply_text("Status is not available.")
            return
        await update.message.reply_text(await self._statusProvider())

    async def _setChatSetting(self, update: Update, command: str, setter, value: bool, reply: str) -> None:
        styler.info(f"Received /{command} command")
        if not setter(update.effective_chat.id, value):
            await update.message.reply_text("You are not subscribed. Send /start first.")
            return
        await update.message.reply_text(reply)

    async def sendCustomMessage(self, message: str, chat_id: int = None, chat_ids: Optional[List[int]] = None) -> bool:
        """
        Send a custom message to bot chat(s).
        
        Args:
            message (str): The message to send
            chat_id (int, optional): Specific chat ID to send to. If None, sends to all known chats.
            chat_ids (List[int], optional): Send only to these chats instead of all known chats.
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        styler.printSeparator()

        if not self._tgApp:
            styler.error("Bot is not initialized!")
            return False
        
        try:
            if chat_id:
                # Send to specific chat
                await self._tgApp.bot.send_message(chat_id=chat_id, text=message)
                return True

            
            chatIdArray = chat_ids if chat_ids is not None else storageService.getAllChatIds()

            # Send to all known chats
            if not chatIdArray:
                styler.error("No chat IDs available. Users need to interact with the bot first.")
                return False
            
            success_count = 0
            for cid in chatIdArray.copy():  # Use copy to avoid modification during iteration
                try:
                    await self._tgApp.bot.send_message(chat_id=cid, text=message)
                    success_count += 1
                except Forbidden as e:
                    # User blocked the bot or removed it from the group: stop sending to this chat
                    styler.warning(f"Chat {cid} is not available anymore ({e}). Unsubscribing it.")
                    storageService.deactivate_chat_id(cid)
                except Exception as e:
                    styler.error(f"Failed to send message to chat {cid}: {e}")
            
            styler.info(f"Message sent to {success_count}/{len(chatIdArray)} chats: {message}")
            return success_count > 0
                
        except Exception as e:
            styler.error(f"Error sending message: {e}")
            return False


tgService = TgService()
