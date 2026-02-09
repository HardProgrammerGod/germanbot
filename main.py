import asyncio
import logging
import os
from dotenv import load_dotenv # Необхідно для зчитування .env
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
from aiohttp import web

# Завантажуємо змінні з файлу .env
load_dotenv()

# --- НАЛАШТУВАННЯ (ЗЧИТУВАННЯ З ОТОЧЕННЯ) ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GIRL_USER = os.getenv("GIRL_USER", "@ni2282")

if not TOKEN:
    exit("Помилка: BOT_TOKEN не знайдено в системних змінних!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {}

LANG_TEXTS = {
    'en': {
        'welcome': "Hey! 👋 Nice to meet you. Let's chat here!",
        'photos': "My private photos 📸",
        'chat': "Chat with me personally 🤗",
        'donate': "Support me (Stars) ⭐",
        'thanks': "Thank you! ❤️ Here is my profile: ",
        'invoice_title': "Premium Access",
        'invoice_desc': "Exclusive content and chat"
    },
    'de': {
        'welcome': "Hey! 👋 Schön, dass du mich gefunden hast. Lass uns hier schreiben!",
        'photos': "Meine privaten Fotos 📸",
        'chat': "Mit mir persönlich chatten 🤗",
        'donate': "Unterstütze mich (Stars) ⭐",
        'thanks': "Danke! ❤️ Hier ist mein Profil: ",
        'invoice_title': "Premium Zugang",
        'invoice_desc': "Exklusiver Content und Chat"
    },
    'es': {
        'welcome': "¡Hola! 👋 Qué bueno que me encontraste. ¡Hablemos por aquí!",
        'photos': "Mis fotos privadas 📸",
        'chat': "Chatea conmigo personalmente 🤗",
        'donate': "Apóyame (Estrellas) ⭐",
        'thanks': "¡Gracias! ❤️ Aquí está mi perfil: ",
        'invoice_title': "Acceso Premium",
        'invoice_desc': "Contenido exclusivo y chat"
    }
}

DONATE_AMOUNTS = [100, 250, 300, 500, 750, 1000, 2500, 5000, 10000]

async def handle(request):
    return web.Response(text="Bot is running!")

# --- ОБРОБНИКИ ---

@dp.message(Command("start"))
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Немає"
    full_name = message.from_user.full_name
    
    ref_code = command.args if command.args else "Прямий вхід"

    admin_msg = (
        f"🔔 **Новий користувач!**\n\n"
        f"👤 Ім'я: {full_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔗 Нік: {username}\n"
        f"🎟 Реф. посилання: `{ref_code}`"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Адмін не отримав сповіщення: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en")],
        [InlineKeyboardButton(text="Deutsch 🇩🇪", callback_data="lang_de")],
        [InlineKeyboardButton(text="Español 🇪🇸", callback_data="lang_es")]
    ])
    await message.answer("Please choose your language:", reply_markup=kb)

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    user_data[callback.from_user.id] = {'lang': lang, 'purchased': False}
    
    texts = LANG_TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts['photos'], callback_data="buy_photos")],
        [InlineKeyboardButton(text=texts['chat'], callback_data="buy_chat")],
        [InlineKeyboardButton(text=texts['donate'], callback_data="menu_donate")]
    ])
    
    await callback.message.edit_text(texts['welcome'], reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "menu_donate")
async def show_donate_menu(callback: types.CallbackQuery):
    lang = user_data.get(callback.from_user.id, {}).get('lang', 'en')
    
    buttons = []
    row = []
    for amount in DONATE_AMOUNTS:
        row.append(InlineKeyboardButton(text=f"⭐ {amount}", callback_data=f"star_{amount}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"lang_{lang}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Choose donation amount:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith(("buy_", "star_")))
async def create_invoice(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = user_data.get(user_id, {}).get('lang', 'en')
    texts = LANG_TEXTS[lang]
    
    data_parts = callback.data.split("_")
    action, value = data_parts[0], data_parts[1]

    amount = 490 if value == "photos" else 990 if value == "chat" else int(value)

    await callback.message.answer_invoice(
        title=texts['invoice_title'],
        description=texts['invoice_desc'],
        payload=f"pay_{value}",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: types.Message):
    user_id = message.from_user.id
    lang = user_data.get(user_id, {}).get('lang', 'en')
    texts = LANG_TEXTS[lang]

    if user_id in user_data:
        user_data[user_id]['purchased'] = True
    
    await message.answer(f"{texts['thanks']}{GIRL_USER}")
    await bot.send_message(ADMIN_ID, f"💰 **ОПЛАТА** ({message.successful_payment.total_amount} Stars) від {message.from_user.full_name}")

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    asyncio.create_task(site.start())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
