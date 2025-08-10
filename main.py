import asyncio
import nest_asyncio
nest_asyncio.apply()

import os
import logging
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# States
ASKING_QUESTION = 1
REAL_TIME_DETECTION = 2

# Helper: Main menu keyboard
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🔔 Notification Alert", callback_data='alert')],
        [InlineKeyboardButton("📊 Real Time Detection", callback_data='real_time')],
        [InlineKeyboardButton("⚙️ Import Settings", callback_data='import_settings')],
        [InlineKeyboardButton("❓ Need Help?", callback_data='need_help')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Unified function to send or edit the main menu
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends or edits a message with the main menu."""
    text = (
        "✨ <b>Welcome to the Assistant Bot!</b> ✨\n\n"
        "I'm here to help you manage your groups, answer questions, and more.\n"
        "Choose an option below to get started:"
    )
    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=get_main_menu(), parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Failed to send/edit main menu: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=get_main_menu(), parse_mode='HTML'
            )
    return ConversationHandler.END

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Bot started by user %s", update.effective_user.id)
    return await send_main_menu(update, context)

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data:
        return


    try:
        if query.data == 'real_time':
            return await real_time_detection(update, context)
        elif query.data == 'need_help':
            return await help_command(update, context)
        elif query.data == 'import_settings':
            return await import_settings(update, context)
        elif query.data == 'alert':
            return await alert_user(update, context)
        else:
            return await send_main_menu(update, context)

    except Exception as e:
        logger.error("Error in button_handler: %s", e)
        await query.message.reply_text(
            "⚠️ An error occurred. Please try again.", reply_markup=get_main_menu()
        )

# Back to main menu
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await send_main_menu(update, context)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Help command used by user %s", update.effective_user.id)

    text = (
        "📘 <b>Help Center</b>\n\n"
        "I can help you with:\n"
        "• Answering simple questions\n"
        "• Managing group settings (soon)\n"
        "• Providing useful tools\n\n"
        "<b>Commands:</b>\n"
        "• /start – Start the bot\n"
        "• /help – Show this message\n"
        "• /ask – Ask me anything\n"
        "• /clear – Clean up chat"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Error in help_command: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )

# Clear command
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear recent chat history and restart the bot experience."""
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    # Reset user context
    context.user_data.clear()
    logger.info("Cleared user_data for user %s", update.effective_user.id)

    # Delete up to 6 recent messages (including /clear)
    deleted = 0
    for offset in range(0, 6):
        try:
            mid = message_id - offset
            if mid > 0:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted += 1
        except Exception:
            pass  # Message not found or restricted

    logger.info("User %s reset the chat. %d messages deleted.", update.effective_user.id, deleted)
    return await send_main_menu(update, context)

# Ask command
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Ask command used by user %s", update.effective_user.id)

    text = (
        "🧠 <b>Ask a Question</b>\n\n"
        "Type your message below. I'll do my best to help!\n"
        "Use /cancel to stop anytime."
    )

    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    return ASKING_QUESTION

# Handle question responses
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await update.message.reply_text("Please send a valid text question.")
        return ASKING_QUESTION

    user_message = update.message.text.lower().strip()

    # Simple AI-like responses
    if any(greeting in user_message for greeting in ("hello", "hi", "hey", "yo")):
        response = "👋 Hello there! How can I help you today?"
    elif any(farewell in user_message for farewell in ("bye", "goodbye", "see you", "later")):
        response = "👋 Goodbye! Feel free to ask more anytime."
    elif "how are you" in user_message:
        response = "🙂 I'm doing great, thanks for asking! How about you?"
    elif "thank" in user_message:
        response = "😊 You're welcome!"
    else:
        response = (
            "🔍 I'm not sure I understand.\n"
            "Try asking something like:\n"
            "• Hi\n"
            "• How are you?\n"
            "• What can you do?"
        )

    await update.message.reply_text(response)
    return ASKING_QUESTION

# Cancel conversation
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("User %s cancelled the conversation.", update.effective_user.id)
    await update.message.reply_text(
        "❌ Question mode cancelled. Use /ask to start again.",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

# Notification Alert
async def alert_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Notification alert triggered by user %s", update.effective_user.id)
    text = "🔔 Notification alert is now active."
    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Failed to send notification alert: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )

# Real time detection
async def real_time_detection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Real time detection triggered by user %s", update.effective_user.id)
    text = "📊 Real Time Detection is under development. Stay tuned for updates!"
    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Failed to send real time detection message: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
# importing setting
async def import_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Importing settings..."
    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Failed to send real time detection message: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=reply_markup, parse_mode='HTML'
            )
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "Error while handling update %s: %s",
        update.update_id if update else "unknown",
        context.error,
        exc_info=context.error
    )
    try:
        if update and update.message:
            await update.message.reply_text(
                "⚠️ An error occurred. Please try again later."
            )
        elif update and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                "⚠️ An error occurred. Please try again later."
            )
    except Exception:
        pass  # Fallback in case reply fails

# Main function
async def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN is missing!")
        return

    application = Application.builder().token(bot_token).build()

    # Conversation handler for Q&A
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask_command)],
        states={
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CommandHandler("help", help_command),
            CommandHandler("start", start_command),
        ],
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Set bot commands
    await application.bot.set_my_commands([
        BotCommand("start", "🔁 Restart or start the bot"),
        BotCommand("help", "📘 Show help menu"),
        BotCommand("ask", "🧠 Ask a question"),
        BotCommand("clear", "🧹 Clear recent messages"),
    ])

    logger.info("Bot is running...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())