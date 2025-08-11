from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from dotenv import load_dotenv
import os
from bot.handlers import (
    start_command, help_command, clear_command, profile_command, results_command,
    button_handler, error_handler, create_exam_conversation_handler
)
from bot.scheduler import setup_scheduler, scheduler
import logging
import asyncio

logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    """Main function to set up and run the bot."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is missing!")
        return

    global application
    application = (
        Application.builder()
        .token(bot_token)
        .concurrent_updates(True)
        .build()
    )

    # Register handlers
    application.add_handler(create_exam_conversation_handler())
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("results", results_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Error handler
    application.add_error_handler(error_handler)

    # Set bot commands (Khmer translated)
    bot_commands = [
        BotCommand("start", "🏠 មុខងារមេនយូ និងស្វាគមន៍"),
        BotCommand("help", "❓ ជំនួយ និង មជ្ឈមណ្ឌលគាំទ្រ"),
        BotCommand("profile", "👤 មើលប្រវត្តិរូប និងស្ថិតិរបស់អ្នក"),
        BotCommand("results", "📊 មើលលទ្ធផលការប្រឡងរបស់អ្នក"),
        BotCommand("clear", "🧹 សម្អាតសន្ទនា និងកំណត់ឡើងវិញសម័យ"),
    ]
    await application.bot.set_my_commands(bot_commands)

    # Set bot description in Khmer
    await application.bot.set_my_description(
        "🎓 ប្រព័ន្ធការប្រឡងសាលា​គ្រប់គ្រង - ធ្វើការប្រឡងផ្ទាល់ខ្លួន, តាមដានមុខងារ និងបង្កើនចំណេះដឹងរបស់អ្នកដោយការផ្តល់មតិយោបល់ភ្លាមៗ!"
    )
    await application.bot.set_my_short_description(
        "🎓 ប្រព័ន្ធការប្រឡងសាលាគ្រប់គ្រងផ្ទាល់ខ្លួន"
    )

    # Set up scheduler
    try:
        setup_scheduler(application)
        if scheduler is None:
            logger.error("Scheduler is None, cannot start")
        else:
            scheduler.start()  # Start scheduler in the bot's event loop
            logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)

    logger.info("🚀 ប្រព័ន្ធបច្ចុប្បន្នរបស់គណនីការប្រឡងកំពុងដំណើរការ...")
    logger.info("📊 ការប្រឡងដែលមានស្រាប់ត្រូវបានផ្ទុករួចរាល់")
    logger.info("🔧 មុខងារ៖ UI អភិវឌ្ឍន៍, មតិយោបល់ពេលពិត, ការតាមដានមុខងារ")

    try:
        await application.initialize()  # Explicitly initialize the application
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error("Error running bot: %s", e)
    finally:
        if scheduler is not None:
            await scheduler.shutdown(wait=False)  # Await scheduler shutdown
            logger.info("🛑 Scheduler stopped")
        await application.shutdown()  # Ensure application shutdown
        logger.info("🛑 ប្រព័ន្ធបញ្ចប់ដំណើរការ")
