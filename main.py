import asyncio
from dotenv import load_dotenv
load_dotenv()  #
from webbrowser import get
import nest_asyncio
nest_asyncio.apply()

import logging
import threading
import os
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import streamlit as st
from datetime import datetime


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_logs.log"),  # Save logs to a file
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        header_text = "Welcome to the Bot!"
        subheader_text = "I am here to assist you with various tasks."
        body_text = "Feel free to ask me anything using /help"

        logger.info("Bot started")
        context.user_data['is_asking'] = False

        full_message = f"{header_text}\n{subheader_text}\n{body_text}"
        await update.message.reply_text(full_message)
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("Help command invoked")
        header_text = "Here are the commands you can use:"
        subheader_text = "1. /start - Start the bot\n2. /help - Get help information\n3. /clear - Clear the chat\n4. /ask - Ask a question"
        logger.info(f"Header: {header_text}")
        logger.info(f"Subheader: {subheader_text}")

        context.user_data['is_asking'] = False

        full_message = f"{header_text}\n{subheader_text}"
        await update.message.reply_text(full_message)
    except Exception as e:
        logger.error(f"Error in help command: {e}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat_id
        from_message_id = update.message.message_id

        for msg_id in range(from_message_id, from_message_id - 100, -1):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass

        context.user_data['is_asking'] = False
    except Exception as e:
        logger.error(f"Error in clear command: {e}")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        header_text = "Ask a Question"
        subheader_text = "Please type your question below. I will try to assist you."

        context.user_data['is_asking'] = True

        full_message = f"{header_text}\n{subheader_text}\n"
        await update.message.reply_text(full_message)
    except Exception as e:
        logger.error(f"Error in ask command: {e}")

async def ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.user_data.get('is_asking', False):
            await update.message.reply_text("Please use /ask to ask a question.")
            return

        ai_response = ""
        if update.message and update.message.text:
            user_message = update.message.text.lower()
            if "hello" in user_message or "hi" in user_message:
                ai_response = "Hello! How can I help you?"
            elif "bye" in user_message or "goodbye" in user_message:
                ai_response = "Goodbye! Have a nice day!"
            else:
                ai_response = "I didn't understand that. Please try again."
        else:
            logger.info("No text message found in the update.")
            ai_response = "Please provide a valid question."

        await update.message.reply_text(ai_response)
        context.user_data['is_asking'] = False
    except Exception as e:
        logger.error(f"Error in AI response: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.error(f"Update {update} caused error {context.error}")
        await update.message.reply_text("An error occurred while processing your request.")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
    finally:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred while processing your request.")

async def main():
    bot_token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_response))
    application.add_error_handler(error_handler)

    # Suggest commands when typing "/"
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Get help information"),
        BotCommand("clear", "Clear the chat"),
        BotCommand("ask", "Ask a question")
    ])

    # Start polling
    await application.run_polling()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())

    