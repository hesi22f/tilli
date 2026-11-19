import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

async def main():
    # ۱. راه‌اندازی دیتابیس
    await init_db()
    
    # ۲. ساخت ربات و دیسپچر
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # ۳. اضافه کردن هندلرها
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    print("✅ ربات Tilicoin با موفقیت روشن شد...")
    
    # ۴. شروع دریافت پیام‌ها
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("ربات متوقف شد.")
