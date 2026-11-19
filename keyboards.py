from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="⛏️ شروع ماین", callback_data="mine", style="success")],
        [InlineKeyboardButton(text="👥 دعوت دوستان", callback_data="referral", style="primary")],
        [InlineKeyboardButton(text="🎯 انجام ماموریت", callback_data="missions", style="danger")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="account", style="primary")],
        [InlineKeyboardButton(text="💸 برداشت", callback_data="withdraw", style="success")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠️ پنل مدیریت", callback_data="admin_panel", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def plans_menu(active_plan: int):
    buttons = []
    labels = {
        1: "🎁 پلن خوش‌آمدگویی (۵ رفرال)",
        2: "🥉 پلن برنزی - ۱ TON",
        3: "🥈 پلن نقره‌ای - ۲ TON",
        4: "🥇 پلن طلایی - ۳ TON",
    }
    for pid, label in labels.items():
        if pid == active_plan:
            label = "✅ " + label
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"plan_{pid}", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_menu", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def join_channels_keyboard(channels: list[str]):
    buttons = []
    for ch in channels:
        clean = ch.replace("@", "")
        buttons.append([InlineKeyboardButton(text=f"📢 {ch}", url=f"https://t.me/{clean}", style="primary")])
    buttons.append([InlineKeyboardButton(text="✅ عضو شدم", callback_data="check_join", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_menu", style="danger")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار", callback_data="admin_stats", style="primary")],
        [InlineKeyboardButton(text="💰 تایید پرداخت‌ها", callback_data="admin_payments", style="success")],
        [InlineKeyboardButton(text="📢 مدیریت کانال‌ها", callback_data="admin_channels", style="danger")],
        [InlineKeyboardButton(text="📨 پیام همگانی", callback_data="admin_broadcast", style="primary")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_menu", style="danger")],
    ])