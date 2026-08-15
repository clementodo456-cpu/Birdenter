import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

COMMON_TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "America/New_York",
    "America/Los_Angeles", "Asia/Dubai", "Asia/Kolkata",
    "Asia/Singapore", "Africa/Lagos", "Australia/Sydney"
]

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_tz = db.get_user_timezone(user_id)
    stats = db.get_user_stats(user_id)
    
    text = (
        f"⚙️ <b>Settings & Statistics</b>\n\n"
        f"🌍 <b>Current Timezone:</b> <code>{current_tz}</code>\n\n"
        f"📊 <b>Stats:</b>\n"
        f"• Total Reminders: {stats['total']}\n"
        f"• Active Reminders: {stats['active']}\n"
        f"• Completed: {stats['completed']}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Change Timezone", callback_data="SET_TZ_MENU")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]
    ])
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def timezone_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    buttons = []
    for tz in COMMON_TIMEZONES:
        buttons.append([InlineKeyboardButton(tz, callback_data=f"SET_TZ_SELECT_{tz}")])
        
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="NAV_SETTINGS")])
    keyboard = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text("🌍 Select your timezone:", reply_markup=keyboard)

async def set_timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tz_name = query.data.replace("SET_TZ_SELECT_", "")
    user_id = update.effective_user.id
    
    if db.set_user_timezone(user_id, tz_name):
        await query.edit_message_text(f"✅ Timezone updated to <b>{tz_name}</b>!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Back to Settings", callback_data="NAV_SETTINGS")]]), parse_mode="HTML")
    else:
        await query.edit_message_text("❌ Failed to update timezone.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Back to Settings", callback_data="NAV_SETTINGS")]]))
