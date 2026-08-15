from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Reminder", callback_data="NAV_ADD"), InlineKeyboardButton("📅 My Reminders", callback_data="NAV_REMINDERS")],
        [InlineKeyboardButton("🗓️ Calendar", callback_data="NAV_CALENDAR"), InlineKeyboardButton("⚙️ Settings", callback_data="NAV_SETTINGS")],
        [InlineKeyboardButton("❓ Help", callback_data="NAV_HELP")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"👋 Welcome, <b>{user.first_name}</b>!\n\n"
        f"I am <b>@BirdEntertainmentSBS24bot</b>, your personal Calendar Reminder Assistant.\n"
        f"I can help you keep track of events, tasks, meetings, and birthdays effortless!\n\n"
        f"Choose an option from the menu below to get started:"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ <b>Help & Instructions</b>\n\n"
        "• <b>➕ Add Reminder:</b> Create a new task or event with step-by-step guidance.\n"
        "• <b>📅 My Reminders:</b> View, mark complete, or delete existing reminders.\n"
        "• <b>🗓️ Calendar:</b> Browse dates visually and see scheduled events.\n"
        "• <b>⚙️ Settings:</b> Configure your personal Timezone and view statistics.\n\n"
        "<b>Commands:</b>\n"
        "/start - Launch main menu\n"
        "/reminders - View active reminders\n"
        "/today - View today's schedule\n"
        "/calendar - Interactive calendar view\n"
        "/settings - Timezone & preferences\n"
        "/help - Display this guide"
    )
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="NAV_MAIN_MENU")]])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode="HTML")
