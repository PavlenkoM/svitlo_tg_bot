import html
import logging
import asyncio
from telegram import BotCommand, ForceReply, Update
from telegram.error import Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from utils import styler
from storage import storageService

class TgService:
    _tgApp = None

    async def initBot(self, token: str) -> None:
        styler.info("Starting Telegram bot...")
        self._tgApp = Application.builder().token(token).build()

        # on different commands - answer in Telegram
        self._tgApp.add_handler(CommandHandler("start", self.commandStart))
        self._tgApp.add_handler(CommandHandler("stop", self.commandStop))

        # Initialize the application
        await self._tgApp.initialize()

        # Show the commands in the Telegram menu
        try:
            await self._tgApp.bot.set_my_commands([
                BotCommand("start", "Subscribe to electricity notifications"),
                BotCommand("stop", "Unsubscribe"),
            ])
        except Exception as e:
            styler.warning(f"Failed to set bot commands menu: {e}")
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

    async def sendCustomMessage(self, message: str, chat_id: int = None) -> bool:
        """
        Send a custom message to bot chat(s).
        
        Args:
            message (str): The message to send
            chat_id (int, optional): Specific chat ID to send to. If None, sends to all known chats.
        
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

            
            chatIdArray = storageService.getAllChatIds()

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
