import logging
import asyncio
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from utils import styler

class TgService:
    _tgApp = None
    _chat_ids = set()  # Store chat IDs of users who have interacted with the bot

    async def initBot(self, token: str) -> None:
        print("Starting Telegram bot...")
        self._tgApp = Application.builder().token(token).build()

        # on different commands - answer in Telegram
        self._tgApp.add_handler(CommandHandler("start", self.start))
        # application.add_handler(CommandHandler("help", help_command))
        
        # Initialize the application
        await self._tgApp.initialize()
        print("Telegram bot initialized.")
    
    async def startPolling(self, token) -> None:
        """Start the bot polling"""
        if not self._tgApp:
            await self.initBot(token)

        print("Starting Telegram bot polling...")
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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        print("Received /start command")
        # Store the chat ID for future messaging
        self._chat_ids.add(update.effective_chat.id)
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}!",
            reply_markup=ForceReply(selective=True),
        )

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
            
            # Send to all known chats
            if not self._chat_ids:
                styler.error("No chat IDs available. Users need to interact with the bot first.")
                return False
            
            success_count = 0
            for cid in self._chat_ids.copy():  # Use copy to avoid modification during iteration
                try:
                    await self._tgApp.bot.send_message(chat_id=cid, text=message)
                    success_count += 1
                except Exception as e:
                    styler.error(f"Failed to send message to chat {cid}: {e}")
                    # Optionally remove invalid chat IDs
                    # self._chat_ids.discard(cid)
            
            print(f"Message sent to {success_count}/{len(self._chat_ids)} chats: {message}")
            return success_count > 0
                
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def getChatIds(self) -> list:
        """
        Get list of all stored chat IDs.
        
        Returns:
            list: List of chat IDs
        """
        return list(self._chat_ids)

    def addChatId(self, chat_id: int) -> None:
        """
        Manually add a chat ID for messaging.
        
        Args:
            chat_id (int): Chat ID to add
        """
        self._chat_ids.add(chat_id)


tgService = TgService()
