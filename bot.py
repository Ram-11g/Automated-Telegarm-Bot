import logging
import asyncio
import sys
import signal
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import Conflict

from config import BOT_TOKEN, CHANNEL_ID, DEFAULT_PRODUCTS_COUNT, MAX_PRODUCTS_COUNT
from scraper import scrape_products
from utils import format_product_message

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
bot = None
application = None

async def cleanup():
    """Cleanup function to close bot and application"""
    global bot, application
    if bot:
        await bot.close()
    if application:
        await application.stop()
        await application.shutdown()

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logger.info("Received shutdown signal")
    asyncio.create_task(cleanup())
    sys.exit(0)

async def send_message(update: Update, text: str) -> None:
    """Helper function to safely send messages"""
    try:
        if update.message:
            await update.message.reply_text(text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text)
        else:
            logger.warning("Could not send message: No message or callback query found in update")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    await send_message(update, 
        "Welcome! I'm your Product Bot. Use /post to share products or /post_count <number> to specify how many products to post."
    )

async def post_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /post command"""
    try:
        if not update.effective_message:
            logger.error("No effective message found in update")
            return

        count = DEFAULT_PRODUCTS_COUNT
        if context.args and context.args[0].isdigit():
            count = min(int(context.args[0]), MAX_PRODUCTS_COUNT)
        
        await send_message(update, f"Searching for {count} products. Please wait...")
        
        try:
            products = await scrape_products(num_products=count)
        except Exception as e:
            logger.error(f"Error scraping products: {e}")
            await send_message(update, "Failed to fetch products. Please try again later.")
            return

        if not products:
            await send_message(update, "No products found at the moment. Please try again later.")
            return

        success_count = 0
        for product in products:
            try:
                message = format_product_message(product)
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
                success_count += 1
                await asyncio.sleep(0.5)  # Small delay between messages
            except Exception as e:
                logger.error(f"Error sending product message: {e}")
                continue

        if success_count > 0:
            await send_message(update, f"Successfully posted {success_count} products to the channel!")
        else:
            await send_message(update, "Failed to post any products. Please check the logs for details.")

    except Exception as e:
        logger.error(f"Error in post_products: {e}")
        await send_message(update, "An unexpected error occurred. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/post - Post 5 random products to the channel\n"
        "/post_count <number> - Post specified number of products (max 10)\n"
        "/help - Show this help message"
    )
    await send_message(update, help_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any other text messages"""
    if update.effective_message and update.effective_message.text:
        await send_message(update,
            "I'm a product bot that posts products to a channel. Use /post to share products or /help for more information."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(context.error, Conflict):
        logger.error("Bot conflict detected. Please ensure only one instance is running.")
        await cleanup()
        sys.exit(1)

def main() -> None:
    """Start the bot"""
    global bot, application
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize bot
        bot = Bot(token=BOT_TOKEN)
        
        # Build application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("post", post_products))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("Starting bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        asyncio.run(cleanup())
        sys.exit(1)

if __name__ == '__main__':
    main() 