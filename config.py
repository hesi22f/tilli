import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
TON_WALLET = os.getenv("TON_WALLET", "UQCuQAmDeoCeny3mhAQVVnlC-zIQZHc3RvU8Oq0D4r7qCX3c")

# پلن‌ها: (نام، شرط رفرال، قیمت TON، پاداش روزانه)
PLANS = {
    1: {"name": "پلن خوش‌آمدگویی", "req_ref": 5, "price_ton": 0, "daily_reward": 5},
    2: {"name": "پلن برنزی", "req_ref": 0, "price_ton": 1, "daily_reward": 10},
    3: {"name": "پلن نقره‌ای", "req_ref": 0, "price_ton": 2, "daily_reward": 15},
    4: {"name": "پلن طلایی", "req_ref": 0, "price_ton": 3, "daily_reward": 20},
}

REFERRAL_REWARD = 2          # هر رفرال = ۲ Tilicoin
WITHDRAW_MIN_REFERRALS = 10  # حداقل رفرال برای برداشت