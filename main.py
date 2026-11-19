import asyncio
import logging
import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN
from database import init_db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

# 1. ساخت اپلیکیشن Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 Tilicoin Bot is Running!", 200

# 2. تابع اجرای وب‌سرور Flask (این توی Thread جداگانه اجرا میشه)
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 وب‌سرور روی پورت {port} روشن شد...")
    # استفاده از threaded=False برای جلوگیری از به هم ریختن تردها
    app.run(host="0.0.0.0", port=port, threaded=False, use_reloader=False)

# 3. تابع اصلی اجرای ربات (این توی Main Thread اجرا میشه)
async def start_bot():
    await init_db()
    
    # تنظیم پروکسی فقط برای محیط‌هایی که نیاز دارن (مثل PythonAnywhere)
    # اگر روی Render یا اکشنز هستی، معمولاً نیازی به پروکسی نیست، 
    # ولی اگه خطای اتصال دادی، خط زیر رو آنکامنت کن:
    # session = AiohttpSession(proxy="http://proxy.server:3128")
    # bot = Bot(token=BOT_TOKEN, session=session)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    print("✅ ربات Tilicoin با موفقیت روشن شد...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if name == "main":
    # اجرای Flask در یک Thread پس‌زمینه
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # اجرای ربات در Thread اصلی (این کار خطای set_wakeup_fd رو حل می‌کنه)
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("ربات متوقف شد.")
