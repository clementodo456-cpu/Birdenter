from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import database as db
import scheduler as sc

# Conversation States
TITLE, DATE, TIME, DESCRIPTION, RECURRENCE, CONFIRM = range(6)

async def start_add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    context.user_data.clear()
    msg = "📝 <b>Create New Reminder</b>\n\nPlease enter the <b>Title</b> of your reminder (e.g. <i>Client Meeting</i>):"
    
    if query:
        await query.edit_message_text(msg, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, parse_mode="HTML")
        
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.strip()
    
    prefill_date = context.user_data.get("prefill_date")
    if prefill_date:
        context.user_data["date"] = prefill_date
        await update.message.reply_text(
            f"✅ Date selected from calendar: <b>{prefill_date}</b>\n\nNow enter time in 24h format (e.g. <b>14:30</b>):",
            parse_mode="HTML"
        )
        return TIME

    await update.message.reply_text(
        "📅 Enter the date in format <b>DD/MM/YYYY</b> or <b>YYYY-MM-DD</b> (e.g. <i>20/08/2026</i>):",
        parse_mode="HTML"
    )
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_date = update.message.text.strip()
    parsed_date = None
    
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            pass
            
    if not parsed_date:
        await update.message.reply_text("❌ Invalid date format. Please use <b>DD/MM/YYYY</b> (e.g., 20/08/2026):", parse_mode="HTML")
        return DATE
        
    context.user_data["date"] = parsed_date
    await update.message.reply_text("⏰ Enter time in 24-hour format <b>HH:MM</b> (e.g. <i>14:30</i>):", parse_mode="HTML")
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_time = update.message.text.strip()
    try:
        valid_time = datetime.strptime(raw_time, "%H:%M").strftime("%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Invalid time format. Use 24-hour format <b>HH:MM</b> (e.g., 09:15 or 18:30):", parse_mode="HTML")
        return TIME

    user_id = update.effective_user.id
    tz_str = db.get_user_timezone(user_id)
    user_tz = pytz.timezone(tz_str)
    
    dt_str = f"{context.user_data['date']} {valid_time}"
    naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    local_dt = user_tz.localize(naive_dt)
    now_local = datetime.now(user_tz)

    if local_dt < now_local:
        await update.message.reply_text("⚠️ You cannot set a reminder in the past! Please re-enter a future date or time.", parse_mode="HTML")
        return TIME

    context.user_data["time"] = valid_time
    context.user_data["datetime_iso"] = local_dt.isoformat()

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏩ Skip Description", callback_data="SKIP_DESC")]])
    await update.message.reply_text("📝 Enter optional description or details (or tap Skip):", reply_markup=keyboard, parse_mode="HTML")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query and update.callback_query.data == "SKIP_DESC":
        await update.callback_query.answer()
        context.user_data["description"] = ""
    else:
        context.user_data["description"] = update.message.text.strip()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("One-time", callback_data="REC_none"), InlineKeyboardButton("Daily", callback_data="REC_daily")],
        [InlineKeyboardButton("Weekly", callback_data="REC_weekly"), InlineKeyboardButton("Monthly", callback_data="REC_monthly")],
        [InlineKeyboardButton("Yearly", callback_data="REC_yearly")]
    ])
    
    text = "🔄 Choose reminder repeat schedule:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)
        
    return RECURRENCE

async def get_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rec_type = query.data.replace("REC_", "")
    context.user_data["recurrence"] = rec_type
    
    tz_str = db.get_user_timezone(update.effective_user.id)
    
    summary = (
        f"📋 <b>Confirm Reminder Details:</b>\n\n"
        f"📌 <b>Title:</b> {context.user_data['title']}\n"
        f"📅 <b>Date:</b> {context.user_data['date']}\n"
        f"⏰ <b>Time:</b> {context.user_data['time']} ({tz_str})\n"
        f"📝 <b>Description:</b> {context.user_data.get('description') or 'None'}\n"
        f"🔄 <b>Repeat:</b> {rec_type.capitalize()}\n\n"
        f"Is everything correct?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm & Save", callback_data="CONFIRM_SAVE")],
        [InlineKeyboardButton("❌ Cancel", callback_data="CONFIRM_CANCEL")]
    ])
    
    await query.edit_message_text(summary, reply_markup=keyboard, parse_mode="HTML")
    return CONFIRM

async def save_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "CONFIRM_CANCEL":
        await query.edit_message_text("❌ Reminder creation cancelled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]]))
        context.user_data.clear()
        return ConversationHandler.END

    user_id = update.effective_user.id
    tz_str = db.get_user_timezone(user_id)
    
    rem_id = db.add_reminder(
        user_id=user_id,
        title=context.user_data["title"],
        description=context.user_data.get("description", ""),
        reminder_datetime_iso=context.user_data["datetime_iso"],
        tz_str=tz_str,
        recurrence=context.user_data["recurrence"]
    )
    
    reminder = db.get_reminder_by_id(rem_id)
    sc.schedule_job(context.application.bot, reminder)
    
    context.user_data.clear()
    
    await query.edit_message_text(
        "🎉 <b>Reminder Saved & Scheduled Successfully!</b>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📅 View Reminders", callback_data="NAV_REMINDERS"), InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]]),
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Action cancelled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]]))
    return ConversationHandler.END

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = db.get_user_reminders(user_id, status="active")
    
    if not reminders:
        text = "📭 You have no upcoming active reminders."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create Reminder", callback_data="NAV_ADD")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]
        ])
    else:
        text = f"📅 <b>Your Active Reminders ({len(reminders)}):</b>\n\n"
        buttons = []
        for rem in reminders[:10]:
            dt = datetime.fromisoformat(rem["reminder_datetime"]).strftime("%d %b %Y, %H:%M")
            text += f"• <b>{rem['title']}</b> - <i>{dt}</i> ({rem['recurrence']})\n"
            buttons.append([
                InlineKeyboardButton(f"✅ Complete #{rem['id']}", callback_data=f"REM_DONE_{rem['id']}"),
                InlineKeyboardButton(f"🗑️ Delete #{rem['id']}", callback_data=f"REM_DEL_{rem['id']}")
            ])
            
        buttons.append([InlineKeyboardButton("➕ Add New", callback_data="NAV_ADD"), InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")])
        keyboard = InlineKeyboardMarkup(buttons)
        
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def today_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = db.get_user_today_reminders(user_id)
    
    if not reminders:
        text = "☀️ You have no reminders scheduled for today!"
    else:
        text = "☀️ <b>Today's Schedule:</b>\n\n"
        for rem in reminders:
            dt = datetime.fromisoformat(rem["reminder_datetime"]).strftime("%H:%M")
            text += f"⏰ <b>{dt}</b> - {rem['title']}\n<i>{rem['description'] or ''}</i>\n\n"
            
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU")]])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

async def reminder_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("REM_DONE_"):
        rem_id = int(data.replace("REM_DONE_", ""))
        db.update_reminder_status(rem_id, "completed")
        sc.remove_job(rem_id)
        await query.message.reply_text(f"✅ Reminder #{rem_id} marked as completed!")
        await list_reminders(update, context)
        
    elif data.startswith("REM_DEL_"):
        rem_id = int(data.replace("REM_DEL_", ""))
        db.delete_reminder(rem_id)
        sc.remove_job(rem_id)
        await query.message.reply_text(f"🗑️ Reminder #{rem_id} deleted!")
        await list_reminders(update, context)

add_reminder_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_add_reminder, pattern="^NAV_ADD$"),
        CommandHandler("add", start_add_reminder)
    ],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
            CallbackQueryHandler(get_description, pattern="^SKIP_DESC$")
        ],
        RECURRENCE: [CallbackQueryHandler(get_recurrence, pattern="^REC_")],
        CONFIRM: [CallbackQueryHandler(save_reminder_callback, pattern="^CONFIRM_")]
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)]
)
