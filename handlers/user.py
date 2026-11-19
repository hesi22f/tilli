from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from datetime import datetime, timedelta

from database import async_session
from models import User, PlanPayment, ForceChannel
from keyboards import (
    main_menu, plans_menu, join_channels_keyboard, back_to_menu
)
from config import (
    ADMIN_ID, PLANS, TON_WALLET, REFERRAL_REWARD, WITHDRAW_MIN_REFERRALS
)

router = Router()

class UserStates(StatesGroup):
    waiting_tx_hash = State()

async def get_channels():
    async with async_session() as session:
        result = await session.execute(select(ForceChannel))
        return [row.channel_username for row in result.scalars().all()]

async def check_membership(bot, user_id: int) -> bool:
    channels = await get_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            return False
    return True

async def get_user(user_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

@router.message(CommandStart())
async def start(message: Message, bot):
    user_id = message.from_user.id
    args = message.text.split()
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            referred_by = None
            if len(args) > 1 and args[1].isdigit():
                ref_id = int(args[1])
                if ref_id != user_id:
                    ref_res = await session.execute(select(User).where(User.id == ref_id))
                    ref_user = ref_res.scalar_one_or_none()
                    if ref_user:
                        referred_by = ref_id
                        ref_user.referral_count += 1
                        ref_user.balance += REFERRAL_REWARD  # پاداش رفرال
                        
                        # چک فعال‌سازی خودکار پلن ۱
                        if ref_user.referral_count >= PLANS[1]["req_ref"] and ref_user.active_plan < 1:
                            ref_user.active_plan = 1
                            try:
                                await bot.send_message(
                                    ref_id,
                                    "🎉 تبریک! با رسیدن به ۵ رفرال، **پلن خوش‌آمدگویی** برات فعال شد!\n"
                                    f"💰 حالا روزی {PLANS[1]['daily_reward']} Tilicoin ماین می‌کنی."
                                )
                            except:
                                pass
            
            user = User(id=user_id, referred_by=referred_by)
            session.add(user)
            await session.commit()
    
    if not await check_membership(bot, user_id):
        channels = await get_channels()
        await message.answer(
            "برای استفاده از ربات، اول باید توی کانال‌های زیر عضو بشی:",
            reply_markup=join_channels_keyboard(channels)
        )
        return
    
    await message.answer(
        f"سلام {message.from_user.full_name}! 👋\n"
        "به ربات ماینر **Tilicoin** خوش اومدی.\n\n"
        "از منوی زیر شروع کن:",
        reply_markup=main_menu(user_id == ADMIN_ID)
    )

@router.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery, bot):
    if await check_membership(bot, callback.from_user.id):
        await callback.message.edit_text(
            "✅ عضویتت تایید شد!",
            reply_markup=main_menu(callback.from_user.id == ADMIN_ID)
        )
    else:
        await callback.answer("هنوز تو همه کانال‌ها عضو نشدی!", show_alert=True)

@router.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "منوی اصلی:",
        reply_markup=main_menu(callback.from_user.id == ADMIN_ID)
    )

# ---------- دعوت دوستان ----------
@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery, bot):
    user = await get_user(callback.from_user.id)
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    
    await callback.message.edit_text(
        f"👥 **دعوت دوستان**\n\n"
        f"🔗 لینک رفرال تو:\n`{link}`\n\n"
        f"📊 تعداد رفرال‌های تو: **{user.referral_count}**\n"
        f"🎁 پاداش هر رفرال: {REFERRAL_REWARD} Tilicoin\n"
        f"💸 حداقل رفرال برای برداشت: {WITHDRAW_MIN_REFERRALS}\n\n"
        f"هر کسی با این لینک بیاد، بهت اضافه می‌شه.",
        reply_markup=back_to_menu(),
        parse_mode="Markdown"
    )

# ---------- انجام ماموریت ----------
@router.callback_query(F.data == "missions")
async def missions(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🎯 **ماموریت‌ها**\n\n"
        f"📌 ماموریت فعال:\n"
        f"• دعوت از دوستان: هر رفرال = **{REFERRAL_REWARD} Tilicoin**\n\n"
        f"📊 وضعیت تو:\n"
        f"• تعداد رفرال: {user.referral_count}\n"
        f"• Tilicoin دریافتی از رفرال: {user.referral_count * REFERRAL_REWARD}\n\n"
        f"برای دعوت، از بخش «👥 دعوت دوستان» لینکت رو بگیر.",
        reply_markup=back_to_menu(),
        parse_mode="Markdown"
    )

# ---------- حساب کاربری ----------
@router.callback_query(F.data == "account")
async def account(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    plan_name = PLANS.get(user.active_plan, {}).get("name", "هیچ پلنی فعال نیست")
    
    await callback.message.edit_text(
        f"👤 **حساب کاربری**\n\n"
        f"🆔 آیدی: `{user.id}`\n"
        f"💰 موجودی: **{user.balance} Tilicoin**\n"
        f"👥 تعداد رفرال: {user.referral_count}\n"
        f"🎖️ پلن فعال: **{plan_name}**\n"
        f"📅 عضویت: {user.joined_at.strftime('%Y-%m-%d')}\n"
        f"💸 وضعیت برداشت: {'درخواست داده شده' if user.withdraw_requested else 'ندارد'}",
        reply_markup=back_to_menu(),
        parse_mode="Markdown"
    )

# ---------- شروع ماین ----------
@router.callback_query(F.data == "mine")
async def mine_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"⛏️ **شروع ماین**\n\n"
        f"پلن فعال تو: {PLANS.get(user.active_plan, {}).get('name', 'هیچ')}\n"
        f"موجودی: {user.balance} Tilicoin\n\n"
        f"یکی از پلن‌ها رو انتخاب کن:",
        reply_markup=plans_menu(user.active_plan),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("plan_"))
async def plan_selected(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split("_")[1])
    plan = PLANS[plan_id]
    user = await get_user(callback.from_user.id)
    
    if user.active_plan == plan_id:
        # اجرای ماین
        if user.last_mined_at:
            cooldown = timedelta(hours=24)
            if datetime.utcnow() - user.last_mined_at < cooldown:
                remaining = cooldown - (datetime.utcnow() - user.last_mined_at)
                hours = int(remaining.total_seconds() // 3600)
                await callback.answer(f"⏳ باید {hours} ساعت دیگه صبر کنی.", show_alert=True)
                return
        
        async with async_session() as session:
            await session.execute(
                update(User).where(User.id == user.id).values(
                    balance=user.balance + plan["daily_reward"],
                    last_mined_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        await callback.message.edit_text(
            f"⛏️ **ماین موفق!**\n\n"
            f"💰 +{plan['daily_reward']} Tilicoin\n"
            f"📊 موجودی جدید: **{user.balance + plan['daily_reward']}**",
            reply_markup=back_to_menu()
        )
        return
    
    # فعال‌سازی پلن
    if plan_id == 1:
        if user.referral_count >= PLANS[1]["req_ref"]:
            async with async_session() as session:
                await session.execute(
                    update(User).where(User.id == user.id).values(active_plan=1)
                )
                await session.commit()
            await callback.message.edit_text(
                "✅ پلن خوش‌آمدگویی فعال شد! حالا روزی ۵ Tilicoin ماین می‌کنی.",
                reply_markup=back_to_menu()
            )
        else:
            await callback.answer(f"❌ باید {PLANS[1]['req_ref']} رفرال داشته باشی!", show_alert=True)
        return
    
    # پلن‌های پرداختی
    await state.update_data(plan_id=plan_id)
    await state.set_state(UserStates.waiting_tx_hash)
    await callback.message.edit_text(
        f"💳 **خرید {plan['name']}**\n\n"
        f"💰 مبلغ: **{plan['price_ton']} TON**\n"
        f"📅 پاداش روزانه: **{plan['daily_reward']} Tilicoin**\n\n"
        f"📤 مبلغ رو به آدرس زیر واریز کن:\n"
        f"`{TON_WALLET}`\n\n"
        f"سپس **هش تراکنش (TxHash)** رو همین‌جا بفرست تا ادمین تایید کنه.",
        reply_markup=back_to_menu(),
        parse_mode="Markdown"
    )

@router.message(UserStates.waiting_tx_hash)
async def receive_tx_hash(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    plan_id = data["plan_id"]
    tx_hash = message.text.strip()
    
    async with async_session() as session:
        payment = PlanPayment(user_id=message.from_user.id, plan_id=plan_id, tx_hash=tx_hash)
        session.add(payment)
        await session.commit()
    
    await state.clear()
    await message.answer(
        "✅ هش تراکنش دریافت شد!\n"
        "⏳ پس از تایید ادمین، پلن برات فعال می‌شه.",
        reply_markup=back_to_menu()
    )
    
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 **درخواست خرید پلن**\n\n"
            f"👤 کاربر: `{message.from_user.id}`\n"
            f"🎖️ پلن: {PLANS[plan_id]['name']}\n"
            f"📝 TxHash: `{tx_hash}`\n\n"
            f"برای تایید به پنل مدیریت برو.",
            parse_mode="Markdown"
        )
    except:
        pass

# ---------- برداشت ----------
@router.callback_query(F.data == "withdraw")
async def withdraw(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    
    if user.withdraw_requested:
        await callback.message.edit_text(
            "⏳ درخواست برداشت شما قبلاً ثبت شده و در حال بررسی است.",
            reply_markup=back_to_menu()
        )
        return
    
    if user.referral_count < WITHDRAW_MIN_REFERRALS:
        remaining = WITHDRAW_MIN_REFERRALS - user.referral_count
        await callback.message.edit_text(
            f"💸 **برداشت**\n\n"
            f"❌ برای برداشت باید حداقل **{WITHDRAW_MIN_REFERRALS}** رفرال داشته باشی.\n"
            f"👥 رفرال‌های تو: {user.referral_count}\n"
            f"🔴 هنوز {remaining} نفر مونده.",
            reply_markup=back_to_menu(),
            parse_mode="Markdown"
        )
        return
    
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user.id).values(withdraw_requested=True)
        )
        await session.commit()
    
    await callback.message.edit_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        "⏳ برداشت در حال تست هست، لطفاً منتظر بمانید.",
        reply_markup=back_to_menu()
    )