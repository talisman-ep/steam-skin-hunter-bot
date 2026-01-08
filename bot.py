import asyncio
import random 
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import BOT_TOKEN, UAH_RATE
from database import db
from steam_client import SteamClient

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [
            InlineKeyboardButton(text="📜 Список відстеження", callback_data="show_prices"),
            InlineKeyboardButton(text="💰 Мій інвентар", callback_data="ask_portfolio")
        ],
        [
            InlineKeyboardButton(text="❓ Допомога", callback_data="show_help")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)

    await message.answer(
        "👋 **Привіт, трейдере!**\n"
        "Я Steam Skin Hunter. Я допоможу тобі стежити за ринком CS2.\n\n"
        "Обери дію в меню нижче:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
@dp.message(Command("prices"))
async def cmd_prices(message: types.Message):
    rows = await db.get_latest_price()

    if not rows:
        await message.answer("База даних поки що пуста 🤷‍♂️")
        return

    response = "📊 **Останні ціни:**\n\n"
    for row in rows:
        skin = row['skin_name']
        price = row['price']
        price_uah = float(price) * UAH_RATE
        response += f"🔹 {skin} — **{price} $** (≈{price_uah:.0f} ₴)\n"

    await message.answer(response, parse_mode="Markdown")
    
@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "⚠️ **Помилка!** Ти не вказав назву скіна.\n"
            "Приклад використання:\n"
            "`/add AK-47 | Redline (Field-Tested)`", 
            parse_mode="Markdown"
        )
        return

    skin_name = args[1]
    success = await db.add_track_skin(skin_name)
    
    if success:
        await message.answer(f"✅ Скін **{skin_name}** успішно додано до відстеження!", parse_mode="Markdown")
    else:
        await message.answer(f"ℹ️ Скін **{skin_name}** вже є в твоєму списку.", parse_mode="Markdown")
    
    
@dp.message(Command("check"))
async def cmd_check_inventory(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Приклад: `/check https://steamcommunity.com/profiles/7656...`")
        return

    url = args[1]
    client = SteamClient()
    steam_id = client.extract_steam_id(url)

    if not steam_id:
        await message.answer("❌ Не знайдено SteamID.")
        return

    status_msg = await message.answer(f"🔍 Сканую ID: `{steam_id}`...\n🐢 Увімкнено режим 'Лінивець' (обхід бану Steam)...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as session:
        inventory = await client.get_inventory(session, steam_id)
        
        if not inventory:
            await status_msg.edit_text("❌ Інвентар порожній або прихований.")
            return

        unique_items = len(inventory)
        await status_msg.edit_text(f"📦 Предметів: {unique_items}.\n☕ Починаю оцінку. Це буде довго, але точно.")

        total_sum = 0
        priced_items = []
        failed_items = [] 

        for i, skin_name in enumerate(inventory.keys(), 1):
            if i % 5 == 0 or i == 1:
                await status_msg.edit_text(f"⏳ Оцінюю {i}/{unique_items}: `{skin_name}`...", parse_mode="Markdown")

            price = None
            retries = 5
            
            for attempt in range(retries):
                _, price = await client.get_price(session, skin_name)
                
                if price is not None:
                    sleep_time = random.uniform(3.0, 6.0)
                    await asyncio.sleep(sleep_time)
                    break 
                else:
                    wait_time = 60 + (attempt * 30)
                    if attempt < retries - 1:
                        await status_msg.edit_text(f"⛔ Steam блокує ({skin_name}).\n💤 Охолоджуюсь {wait_time} сек... (Спроба {attempt+1}/{retries})")
                        await asyncio.sleep(wait_time)
            
            if price:
                count = inventory[skin_name]
                item_total = price * count
                total_sum += item_total
                priced_items.append((skin_name, price, count, item_total))
            else:
                failed_items.append(skin_name)

        priced_items.sort(key=lambda x: x[1], reverse=True)

        total_uah = total_sum * UAH_RATE

        report = f"📊 **Інвентар гравця:**\nID: `{steam_id}`\n\n"
        
        for item in priced_items[:10]:
            name, price, count, total = item
            report += f"✅ {name} (x{count}) — **{price} $**\n"

        if failed_items:
            report += f"\n⚠️ **Пропущено {len(failed_items)} предметів** (навіть після 5 спроб)\n"

        report += "\n" + "-"*20 + "\n"
        report += f"💰 **ВСЬОГО: {total_sum:.2f} $** (≈ {total_uah:.0f} ₴)"

        await status_msg.edit_text(report, parse_mode="Markdown")   
        
@dp.message(Command("find"))
async def cmd_find_skin(message: types.Message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("⚠️ Введи назву скіна! Приклад: /find AK-47 | Redline")
        return
    
    skin_name = args[1]
    status_msg = await message.answer(f"🔎 Шукаю ціну для: {skin_name}...")
    
    client = SteamClient()
    async with aiohttp.ClientSession() as session:
        real_name, price = await client.get_price(session, skin_name)
        
    if price:
        await status_msg.edit_text(
            f"✅ **{real_name}**\n"
            f"💰 Найнижча ціна: **{price} $**\n\n"
            f"Щоб додати у відстеження: `/add {real_name}`",
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(
            f"❌ **Не вдалося знайти ціну для:** `{skin_name}`\n\n"
            "🔍 **Можливі причини:**\n"
            "1. **Помилка в назві.** Перевір кожну букву, пробіли та дужки.\n"
            "2. **Це ніж/рукавички?** Спробуй додати зірочку на початку: `★ {skin_name}`\n"
            "3. **Дефіцит.** Цей предмет зараз ніхто не продає на Steam.",
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "show_prices")
async def btn_show_prices(callback: CallbackQuery):
    await callback.answer()
    await cmd_prices(callback.message)

@dp.callback_query(F.data == "show_help")
async def btn_show_help(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🤖 **Як користуватися ботом:**\n\n"
        "🔎 `/find <назва>` — знайти ціну скіна\n"
        "➕ `/add <назва>` — додати у відстеження\n"
        "🎒 `/check <посилання>` — оцінити інвентар\n"
        "📈 `/prices` — твій список бажаного"
    )
    await callback.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "ask_portfolio")
async def btn_ask_portfolio(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🎒 Щоб оцінити інвентар, надішли мені посилання на профіль командою:\n"
        "`/check https://steamcommunity.com/id/твій_профіль`",
        parse_mode="Markdown"
    )
