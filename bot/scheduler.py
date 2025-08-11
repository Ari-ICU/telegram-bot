from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import ContextTypes
import logging
from bot.ui import get_main_menu
from bot.storage import load_user_sessions

logger = logging.getLogger(__name__)

# Initialize scheduler as a global variable
scheduler = AsyncIOScheduler()

async def send_reminder_message(context: ContextTypes.DEFAULT_TYPE):
    """Send periodic exam reminders to users."""
    try:
        bot = context.bot
        sessions = load_user_sessions()
        for user_id in sessions:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        "⏰ <b>Exam Reminder</b>\n\n"
                        "Don't forget to complete your pending exams! "
                        "Head to the main menu to start or continue your learning journey. 🎓"
                    ),
                    parse_mode='HTML',
                    reply_markup=get_main_menu()
                )
                logger.info("Sent reminder to user %s", user_id)
            except Exception as e:
                logger.error("Failed to send reminder to user %s: %s", user_id, e)
    except Exception as e:
        logger.error("Error in send_reminder_message: %s", e)

def setup_scheduler(application):
    """Set up the scheduler with the bot's application context."""
    global scheduler
    if scheduler is None:
        logger.error("Scheduler is None, reinitializing")
        scheduler = AsyncIOScheduler()
    
    try:
        scheduler.add_job(
            send_reminder_message,
            'interval',
            hours=1,  # Change to minutes=1 for testing
            args=[application],
            id='exam_reminder'
        )
        logger.info("Scheduler configured with exam reminder job")
    except Exception as e:
        logger.error("Error setting up scheduler: %s", e)