from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from telegram.ext import Application
import database as db

scheduler = AsyncIOScheduler()

async def trigger_reminder_notification(bot, reminder_id: int):
    reminder = db.get_reminder_by_id(reminder_id)
    if not reminder or reminder["status"] != "active":
        return

    user_id = reminder["user_id"]
    title = reminder["title"]
    desc = reminder["description"] or "No details provided."
    recurrence = reminder["recurrence"]
    tz_str = reminder["timezone"]

    text = (
        f"⏰ <b>REMINDER ALERT!</b>\n\n"
        f"📌 <b>Title:</b> {title}\n"
        f"📝 <b>Details:</b> {desc}\n"
        f"🔄 <b>Recurrence:</b> {recurrence.capitalize()}\n\n"
        f"<i>Have a great day!</i>"
    )

    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending reminder {reminder_id} to {user_id}: {e}")

    # Handle Recurrence logic
    if recurrence == "none":
        db.update_reminder_status(reminder_id, "completed")
    else:
        current_dt = datetime.fromisoformat(reminder["reminder_datetime"])
        user_tz = pytz.timezone(tz_str)
        
        if recurrence == "daily":
            next_dt = current_dt + timedelta(days=1)
        elif recurrence == "weekly":
            next_dt = current_dt + timedelta(weeks=1)
        elif recurrence == "monthly":
            # Roughly advance 30 days or handle month rollover cleanly
            month = current_dt.month % 12 + 1
            year = current_dt.year + (current_dt.month // 12)
            day = min(current_dt.day, 28)
            next_dt = current_dt.replace(year=year, month=month, day=day)
        elif recurrence == "yearly":
            next_dt = current_dt.replace(year=current_dt.year + 1)
        else:
            db.update_reminder_status(reminder_id, "completed")
            return

        db.update_reminder_datetime(reminder_id, next_dt.isoformat())
        # Re-schedule job
        job_id = f"reminder_{reminder_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            
        scheduler.add_job(
            trigger_reminder_notification,
            trigger=DateTrigger(run_date=next_dt, timezone=user_tz),
            args=[bot, reminder_id],
            id=job_id,
            replace_existing=True
        )

def schedule_job(bot, reminder: dict):
    reminder_id = reminder["id"]
    job_id = f"reminder_{reminder_id}"
    tz_str = reminder["timezone"]
    user_tz = pytz.timezone(tz_str)
    
    dt = datetime.fromisoformat(reminder["reminder_datetime"])
    if dt.tzinfo is None:
        dt = user_tz.localize(dt)

    now = datetime.now(user_tz)
    
    # If the time is in the past for a one-time reminder, skip scheduling
    if dt < now and reminder["recurrence"] == "none":
        db.update_reminder_status(reminder_id, "expired")
        return

    scheduler.add_job(
        trigger_reminder_notification,
        trigger=DateTrigger(run_date=dt, timezone=user_tz),
        args=[bot, reminder_id],
        id=job_id,
        replace_existing=True
    )

def remove_job(reminder_id: int):
    job_id = f"reminder_{reminder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

def init_scheduler(app: Application):
    scheduler.start()
    active_reminders = db.get_active_reminders()
    for rem in active_reminders:
        schedule_job(app.bot, rem)
