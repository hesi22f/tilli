from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update, delete

from database import async_session
from models import User, PlanPayment, ForceChannel
from keyboards import admin_menu, back_to_menu
from config import ADMIN_ID, PLANS

router = Router()

class AdminStates(StatesGroup):
    waiting_broadcast = State()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🛠️ **پنل مدیریت**", reply_markup=admin_menu())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar()
        total_mined = (await session.execute(select(func.sum(User.balance)))).scalar() or 0
        pending = (await session.execute(
            select(func.count(PlanPayment.id)).where(PlanPayment.status == "pending")
        )).scalar()
    
    await callback.message.edit_text(
        f"📊 **آمار ربات**\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"💰 مجموع Tilicoin: {total_mined}\n"
        f"⏳ پرداخت‌های در انتظار: {pending}",
        reply_markup=back_to_menu()
    )

@router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(PlanPayment).where(PlanPayment.status == "pending")
        )
        payments = result.scalars().all()
    
    if not payments:
        await callback.message.edit_text(
            "✅ هیچ پرداخت در انتظاری نیست.",
            reply_markup=back_to_menu()
        )
        return
    
    for p in payments:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_{p.id}", style="success"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"reject_{p.id}", style="danger"),
            ]
        ])
        await callback.message.answer(
            f"💰 **پرداخت #{p.id}**\n"
            f"👤 کاربر: `{p.user_id}`\n"
            f"🎖️ پلن: {PLANS[p.plan_id]['name']}\n"
            f"📝 TxHash: `{p.tx_hash}`",
            reply_markup=kb,
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        result = await session.execute(select(PlanPayment).where(PlanPayment.id == pid))
        payment = result.scalar_one_or_none()
        if not payment or payment.status != "pending":
            await callback.answer("پرداخت معتبر نیست.", show_alert=True)
            return
        
        payment.status = "approved"
        await session.execute(
            update(User).where(User.id == payment.user_id).values(active_plan=payment.plan_id)
        )
        await session.commit()
    
    await callback.message.edit_text(f"✅ پرداخت #{pid} تایید شد.")
    try:
        await bot.send_message(
            payment.user_id,
            f"🎉 پرداخت شما تایید شد!\n"
            f"🎖️ پلن **{PLANS[payment.plan_id]['name']}** فعال شد.\n"
            f"💰 حالا روزی {PLANS[payment.plan_id]['daily_reward']} Tilicoin ماین می‌کنی."
        )
    except:
        pass

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split("_")[1])
    
    async with async_session() as session:
        result = await session.execute(select(PlanPayment).where(PlanPayment.id == pid))
        payment = result.scalar_one_or_none()
        if not payment or payment.status != "pending":
            await callback.answer("پرداخت معتبر نیست.", show_alert=True)
            return
        payment.status = "rejected"
        await session.commit()
    
    await callback.message.edit_text(f"❌ پرداخت #{pid} رد شد.")
    try:
        await bot.send_message(
            payment.user_id,
            "❌ متأسفانه پرداخت شما تایید نشد. لطفاً با پشتیبانی تماس بگیر."
        )
    except:
        pass

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        result = await session.execute(select(ForceChannel))
        channels = [row.channel_username for row in result.scalars().all()]
    
    text = "📢 **کانال‌های اجباری:**\n\n"
    text += "\n".join(f"• {ch}" for ch in channels) if channels else "هیچ کانالی تنظیم نشده."
    text += "\n\n`/add_channel @channel`\n`/del_channel @channel`"
    
    await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="Markdown")

@router.message(Command("add_channel"))
async def add_channel(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        ch = message.text.split()[1]
        if not ch.startswith("@"):
            ch = "@" + ch
        async with async_session() as session:
            session.add(ForceChannel(channel_username=ch))
            await session.commit()
        await message.answer(f"✅ {ch} اضافه شد.")
    except:
        await message.answer("❌ `/add_channel @channel`", parse_mode="Markdown")

@router.message(Command("del_channel"))
async def del_channel(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        ch = message.text.split()[1]
        if not ch.startswith("@"):
            ch = "@" + ch
        async with async_session() as session:
            await session.execute(delete(ForceChannel).where(ForceChannel.channel_username == ch))
            await session.commit()
        await message.answer(f"✅ {ch} حذف شد.")
    except:
        await message.answer("❌ `/del_channel @channel`", parse_mode="Markdown")

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.edit_text(
        "📨 متن پیام همگانی رو بفرست:",
        reply_markup=back_to_menu()
    )

@router.message(AdminStates.waiting_broadcast)
async def do_broadcast(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return
    async with async_session() as session:
        result = await session.execute(select(User.id))
        user_ids = [row[0] for row in result.all()]
    
    success = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 **اطلاعیه:**\n\n{message.text}")
            success += 1
        except:
            pass
    
    await state.clear()
    await message.answer(f"✅ ارسال به {success}/{len(user_ids)} کاربر.")
