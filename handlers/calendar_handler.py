from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from calendar_utils import build_calendar

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now()
    
    active_reminders = db.get_user_reminders(user_id, status="active")
    marked_days = {
        datetime.fromisoformat(r["reminder_datetime"]).strftime("%Y-%m-%d")
        for r in active_reminders
    }
    
    keyboard = build_calendar(now.year, now.month, marked_days)
    text = "🗓️ <b>Calendar View</b>\nDays with scheduled reminders are highlighted with 📌."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    
    if data == "CAL_IGNORE":
        return

    user_id = update.effective_user.id
    
    if data.startswith("CAL_NAV_"):
        parts = data.split("_")
        year, month = int(parts[2]), int(parts[3])
        
        active_reminders = db.get_user_reminders(user_id, status="active")
        marked_days = {
            datetime.fromisoformat(r["reminder_datetime"]).strftime("%Y-%m-%d")
            for r in active_reminders
        }
        
        keyboard = build_calendar(year, month, marked_days)
        await query.edit_message_text("🗓️ <b>Calendar View</b>\nDays with scheduled reminders are marked with 📌.", reply_markup=keyboard, parse_mode="HTML")
        
    elif data.startswith("CAL_DAY_"):
        selected_date = data.replace("CAL_DAY_", "")
        reminders = db.get_user_date_reminders(user_id, selected_date)
        
        text = f"📅 <b>Reminders for {selected_date}:</b>\n\n"
        if not reminders:
            text += "<i>No scheduled reminders for this date.</i>"
        else:
            for rem in reminders:
                dt_time = datetime.fromisoformat(rem["reminder_datetime"]).strftime("%H:%M")
                text += f"⏰ <b>{dt_time}</b> - {rem['title']}\n"
                
        context.user_data["prefill_date"] = selected_date
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Reminder on this date", callback_data="NAV_ADD")],
            [InlineKeyboardButton("🗓️ Back to Calendar", callback_data="NAV_CALENDAR")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
