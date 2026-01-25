import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiohttp import web

# --- НАСТРОЙКИ (БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ) ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GIRL_USER = os.getenv("GIRL_USERNAME", "@default_profile")

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_states = {}

PRICES = {'photos': 490, 'chat': 990}

async def handle(request):
    return web.Response(text="Bot is running!")

async def delayed_upsell(user_id: int):
    await asyncio.sleep(3600) 
    if user_id in user_states and not user_states[user_id].get('purchased', False):
        try:
            text = "Hey... ich warte immer noch auf dich im Chat. Bist du noch da? 😘"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Lass uns schreiben! ✨", callback_data="buy_chat")]
            ])
            await bot.send_message(user_id, text, reply_markup=kb)
        except: pass

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {'purchased': False}
    
    # Уведомление админу
    admin_msg = f"🔔 **Новый!**\n👤 {message.from_user.full_name}\n📱 [ПРОФИЛЬ](tg://user?id={user_id})"
    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(1.5)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Meine privaten Fotos 📸", callback_data="buy_photos")],
        [InlineKeyboardButton(text="Mit mir persönlich chatten 🤗", callback_data="buy_chat")]
    ])
    await message.answer("Hey! 👋 Schön, dass du mich gefunden hast. Lass uns hier schreiben!", reply_markup=kb)
    asyncio.create_task(delayed_upsell(user_id))

@dp.callback_query(F.data.startswith("buy_"))
async def create_invoice(callback: types.CallbackQuery):
    item = callback.data.split("_")[1]
    await callback.message.answer_invoice(
        title="Premium Access", description="Exklusiver Content", payload=f"payload_{item}",
        currency="XTR", prices=[LabeledPrice(label="Stars", amount=PRICES[item])]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: types.Message):
    if message.from_user.id in user_states:
        user_states[message.from_user.id]['purchased'] = True
    
    await message.answer(f"Danke! ❤️ Hier ist mein Profil: {GIRL_USER}")
    await bot.send_message(ADMIN_ID, f"💰 ОПЛАТА от {message.from_user.full_name}")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    asyncio.create_task(site.start())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
