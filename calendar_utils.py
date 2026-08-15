import calendar
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_calendar(year: int = None, month: int = None, marked_days: set = None) -> InlineKeyboardMarkup:
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    marked_days = marked_days or set()

    keyboard = []
    
    # Month Year Header
    month_name = calendar.month_name[month]
    keyboard.append([
        InlineKeyboardButton(f"{month_name} {year}", callback_data="CAL_IGNORE")
    ])
    
    # Weekday Headers
    weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    keyboard.append([InlineKeyboardButton(day, callback_data="CAL_IGNORE") for day in weekdays])
    
    # Days Grid
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="CAL_IGNORE"))
            else:
                day_str = f"{year}-{month:02d}-{day:02d}"
                text = f"📌{day}" if day_str in marked_days else str(day)
                row.append(InlineKeyboardButton(text, callback_data=f"CAL_DAY_{day_str}"))
        keyboard.append(row)
        
    # Navigation Row
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_row = [
        InlineKeyboardButton("◀️ Prev", callback_data=f"CAL_NAV_{prev_year}_{prev_month}"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="NAV_MAIN_MENU"),
        InlineKeyboardButton("Next ▶️", callback_data=f"CAL_NAV_{next_year}_{next_month}")
    ]
    keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(keyboard)
