import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
import database as db
import scheduler as sc

from handlers.start import start_command, help_command
from handlers.reminders import add_reminder_conv, list_reminders, today_reminders, reminder_action_callback
from handlers.calendar_handler import calendar_command, calendar_callback
from handlers.settings import settings_command, timezone_menu, set_timezone_callback

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN missing in environment variables.")
        raise ValueError("BOT_TOKEN variable must be set!")

    # Initialize SQLite Database
    db.init_db()
    logger.info("Database initialized successfully.")

    # Build Telegram Bot Application
    app = ApplicationBuilder().token(token).build()

    # Initialize Scheduler & Load Reminders from DB
    sc.init_scheduler(app)
    logger.info("Scheduler initialized and jobs reloaded.")

    # Register Handlers
    app.add_handler(add_reminder_conv)
    
    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reminders", list_reminders))
    app.add_handler(CommandHandler("today", today_reminders))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("settings", settings_command))

    # General Callback Query Handlers
    app.add_handler(CallbackQueryHandler(start_command, pattern="^NAV_MAIN_MENU$"))
    app.add_handler(CallbackQueryHandler(list_reminders, pattern="^NAV_REMINDERS$"))
    app.add_handler(CallbackQueryHandler(calendar_command, pattern="^NAV_CALENDAR$"))
    app.add_handler(CallbackQueryHandler(settings_command, pattern="^NAV_SETTINGS$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^NAV_HELP$"))
    
    # Calendar & Settings Callback Handlers
    app.add_handler(CallbackQueryHandler(calendar_callback, pattern="^CAL_"))
    app.add_handler(CallbackQueryHandler(timezone_menu, pattern="^SET_TZ_MENU$"))
    app.add_handler(CallbackQueryHandler(set_timezone_callback, pattern="^SET_TZ_SELECT_"))
    app.add_handler(CallbackQueryHandler(reminder_action_callback, pattern="^REM_"))

    logger.info("Bot started and polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
