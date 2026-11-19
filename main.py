import asyncio
import logging
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

# 1. ساخت اپلیکیشن Flask برای Render
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 Tilicoin Bot is Running!", 200

# 2. تابع اجرای ربات تلگرام
def run_telegram_bot():
    # ساخت یک Event Loop جدید برای این Thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def start_bot():
        # راه‌اندازی دیتابیس
        await init_db()
        
        # تنظیمات ربات
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        
        # اضافه کردن هندلرها
        dp.include_router(user.router)
        dp.include_router(admin.router)
        
        print("✅ ربات Tilicoin با موفقیت روشن شد...")
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()

    # اجرای حلقه ربات
    loop.run_until_complete(start_bot())

# 3. نقطه شروع برنامه
if __name__ == "__main__":
    # شروع ربات در یک Thread پس‌زمینه
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # گرفتن پورت از Render (اگه لوکال بود، پورت 8080)
    port = int(os.environ.get("PORT", 8080))
    
    # شروع وب‌سرور Flask (بلاک‌کننده)
    print(f"🌐 وب‌سرور روی پورت {port} روشن شد...")
    app.run(host="0.0.0.0", port=port)