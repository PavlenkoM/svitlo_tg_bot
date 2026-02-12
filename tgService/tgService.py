import logging
import asyncio
from telegram import ForceReply, Update
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
        
        # Initialize the application
        await self._tgApp.initialize()
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
        """Send a message when the command /start is issued."""
        styler.info("Received /start command")
        # Store the chat ID for future messaging
        storageService.saveChat(update.effective_chat.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)  # Store chat ID in storage service
        user = update.effective_user
        await update.message.reply_html(rf"Hi {user.first_name}!")

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
                except Exception as e:
                    styler.error(f"Failed to send message to chat {cid}: {e}")
                    # Optionally remove invalid chat IDs
                    # self._chat_ids.discard(cid)
            
            styler.info(f"Message sent to {success_count}/{len(chatIdArray)} chats: {message}")
            return success_count > 0
                
        except Exception as e:
            styler.error(f"Error sending message: {e}")
            return False


tgService = TgService()
