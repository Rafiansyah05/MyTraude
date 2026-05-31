"""
Main Telegram bot instance and polling setup.
Integrates all handlers and manages bot lifecycle.
"""

import asyncio
from telegram import Bot, BotCommand
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config.settings import settings
from bot.handlers import BotHandlers
from bot.session_manager import SessionManager
from utils.logger import get_logger

logger = get_logger(__name__)


class TradingBot:
    """Main Telegram bot instance."""
    
    def __init__(self):
        """Initialize bot."""
        self.application: Application = None
        self.bot: Bot = None
    
    async def setup(self):
        """Setup bot and handlers."""
        try:
            # Create application
            self.application = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            
            self.bot = self.application.bot
            
            # Register command handlers
            self.application.add_handler(CommandHandler("start", BotHandlers.handle_start))
            self.application.add_handler(CommandHandler("help", BotHandlers.handle_help))
            self.application.add_handler(CommandHandler("analyze", BotHandlers.handle_analyze))
            self.application.add_handler(CommandHandler("watchlist", BotHandlers.handle_watchlist))
            
            # Register message handler
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.handle_text_message)
            )
            
            # Set up bot commands
            await self._setup_commands()
            
            # Start session cleanup task
            SessionManager.start_cleanup_task()
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error setting up bot: {e}")
            raise
    
    async def _setup_commands(self):
        """Register bot commands in Telegram."""
        try:
            commands = [
                BotCommand("start", "Mulai dengan bot"),
                BotCommand("help", "Lihat bantuan lengkap"),
                BotCommand("analyze", "Mulai analisis trading"),
                BotCommand("watchlist", "Lihat daftar saham"),
            ]
            
            await self.bot.set_my_commands(commands)
            logger.info("Bot commands registered")
        
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")
    
    async def send_notification(self, user_id: int, message: str):
        """Send notification to user."""
        try:
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
            logger.debug(f"Notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending notification to {user_id}: {e}")
    
    async def start(self):
        """Start bot polling."""
        try:
            await self.setup()
            
            logger.info("🤖 Starting Telegram bot polling...")
            logger.info(f"Bot token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")

            await self.application.initialize()
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            await self.application.updater.start_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            await self.application.start()

            logger.info("✅ Bot started and polling successfully")
            while True:
                await asyncio.sleep(1)

        except Conflict as e:
            logger.error(f"Telegram polling conflict: {e}")
            raise
        except asyncio.CancelledError:
            logger.info("Bot polling cancelled")
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            # Cleanup
            await self.stop()
    
    async def stop(self):
        """Stop bot and cleanup."""
        try:
            logger.info("Stopping bot...")
            
            # Stop session cleanup
            await SessionManager.stop_cleanup_task()
            
            # Clear sessions
            SessionManager.clear_all_sessions()
            
            # Close application
            if self.application:
                if self.application.updater and self.application.updater.running:
                    await self.application.updater.stop()
                if self.application.running:
                    await self.application.stop()
                    await self.application.shutdown()
            
            logger.info("Bot stopped")
        
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def run_bot():
    """Run the bot."""
    bot = TradingBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_bot())
