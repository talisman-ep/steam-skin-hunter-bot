import asyncio
import aiohttp
import random
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import BOT_TOKEN, UAH_RATE
from database import db
from steam_client import SteamClient
from monitor import start_monitoring

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

HELP_TEXT = (
    "🤖 **Довідка Steam Skin Hunter**\n\n"
    "🔔 **Сповіщення (НОВЕ!):**\n"
    "• `/alert <назва> <ціна>` — бот напише, коли ціна впаде нижче вказаної.\n"
    "• Приклад: `/alert AWP | Asiimov 45.00`\n\n"
    "🔍 **Аналіз ринку:**\n"
    "• `/find <назва>` — перевірити ціну скіна.\n"
    "• `/check <посилання>` — оцінити весь інвентар (посилання має містити `profiles/765...`).\n\n"
    "💼 **Портфель:**\n"
    "• `/add <назва> [ціна]` — додати скін. Якщо вказати ціну, бот рахуватиме прибуток.\n"
    "• `/del <назва>` — видалити скін зі списку.\n"
    "• `/prices` — показати твій портфель, загальну вартість та PnL (прибуток)."
)

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

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")

@dp.message(Command("alert"))
async def cmd_alert(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer("⚠️ Приклад: `/alert AK-47 | Redline 14.50`", parse_mode="Markdown")
        return
        
    try:
        target_price = float(args[-1].replace(",", "."))
        skin_name = " ".join(args[1:-1])
    except:
        await message.answer("⚠️ Помилка в ціні. Використовуй крапку: 14.50")
        return

    await db.add_track_skin(user_id, skin_name) 
    
    success = await db.set_alert_price(user_id, skin_name, target_price)
    
    if success:
        await message.answer(
            f"🔔 **Сповіщення встановлено!**\n\n"
            f"Я напишу тобі, коли **{skin_name}** буде дешевше **{target_price} $**.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Помилка бази даних.")

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "⚠️ **Формат:** `/add <Назва скіна> [Ціна покупки]`\n"
            "Приклад: `/add AK-47 | Redline (Field-Tested) 15.50`", 
            parse_mode="Markdown"
        )
        return

    buy_price = None
    possible_price = args[-1]
    
    try:
        buy_price = float(possible_price.replace(",", "."))
        skin_name = " ".join(args[1:-1])
    except ValueError:
        skin_name = " ".join(args[1:])
        buy_price = None

    if not skin_name:
         await message.answer("⚠️ Некоректна назва скіна.")
         return

    success = await db.add_track_skin(user_id, skin_name, buy_price)
    
    if success:
        msg_text = f"✅ Скін **{skin_name}** додано!"
        if buy_price:
            msg_text += f"\n🎯 Цільова ціна покупки: **{buy_price} $**"
        
        status_msg = await message.answer(msg_text + "\n⏳ **Отримую актуальну ціну...**", parse_mode="Markdown")

        client = SteamClient()
        try:
            async with aiohttp.ClientSession() as session:
                _, current_price = await client.get_price(session, skin_name)
                
            if current_price:
                await db.add_price(skin_name, current_price)
                await status_msg.edit_text(
                    msg_text + f"\n💵 Поточна ціна: **{current_price} $**", 
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(
                    msg_text + "\n⚠️ Ціну не знайдено (або Steam блокує).", 
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Error fetching initial price: {e}")
            await status_msg.edit_text(msg_text, parse_mode="Markdown")

    else:
        if buy_price:
             await message.answer(f"ℹ️ Скін **{skin_name}** оновлено (нова ціна покупки).", parse_mode="Markdown")
        else:
             await message.answer(f"ℹ️ Скін **{skin_name}** вже є у твоєму списку.", parse_mode="Markdown")

@dp.message(Command("check"))
async def cmd_check_inventory(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Приклад: `/check https://steamcommunity.com/profiles/7656...`", parse_mode="Markdown")
        return

    url = args[1]
    client = SteamClient()

    steam_id = client.extract_steam_id(url)
    
    if not steam_id:
        await message.answer("❌ Не знайдено SteamID (використовуй посилання з `7656...`).")
        return

    status_msg = await message.answer(f"🔍 Сканую ID: `{steam_id}`...\n🐢 Увімкнено режим 'Лінивець' (обхід бану Steam)...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as session:
        inventory = await client.get_inventory(session, steam_id)
        
        if not inventory:
            await status_msg.edit_text("❌ Інвентар порожній, прихований або помилка Steam (спробуй пізніше).")
            return

        unique_items = len(inventory)
        await status_msg.edit_text(f"📦 Унікальних предметів: {unique_items}.\n☕ Починаю повну оцінку. Це довго, але точно.")

        total_sum = 0
        priced_items = []
        failed_items = [] 

        items_list = list(inventory.keys())
        
        for i, skin_name in enumerate(items_list, 1):
            if i % 5 == 0 or i == 1:
                percent = (i / unique_items) * 100
                await status_msg.edit_text(f"⏳ Оцінка {i}/{unique_items} ({percent:.1f}%):\n`{skin_name}`...", parse_mode="Markdown")

            price = None
            retries = 5
            
            for attempt in range(retries):
                _, fetched_price = await client.get_price(session, skin_name)
                
                if fetched_price is not None:
                    price = fetched_price
                    sleep_time = random.uniform(2.5, 4.0) 
                    await asyncio.sleep(sleep_time)
                    break 
                else:
                    wait_time = 10 + (attempt * 10)
                    if attempt == retries - 1:
                         break

                    if attempt > 1:
                        await status_msg.edit_text(f"⛔ Steam думає... ({skin_name})\n💤 Чекаю {wait_time} с...")
                    
                    await asyncio.sleep(wait_time)

            if price:
                count = inventory[skin_name]
                item_total = price * count
                total_sum += item_total
                priced_items.append((skin_name, price, count, item_total))
            else:
                failed_items.append(skin_name)

        priced_items.sort(key=lambda x: x[3], reverse=True)
        total_uah = total_sum * UAH_RATE

        report = f"📊 **Інвентар гравця:**\nID: `{steam_id}`\n\n"

        for item in priced_items[:15]:
            name, p, c, t = item
            report += f"✅ {name} (x{c}) — **{p} $** (Σ {t:.2f})\n"

        if len(priced_items) > 15:
             report += f"...і ще {len(priced_items) - 15} позицій.\n"

        if failed_items:
            report += f"\n⚠️ **Пропущено {len(failed_items)} предметів** (Steam не віддав ціну)\n"

        report += "\n" + "-"*20 + "\n"
        report += f"💰 **ВСЬОГО: {total_sum:.2f} $** (≈ {total_uah:.0f} ₴)"

        await status_msg.edit_text(report, parse_mode="Markdown")

@dp.message(Command("remove", "del"))
async def cmd_remove(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer("⚠️ Приклад: `/del AWP | Asiimov`", parse_mode="Markdown")
        return

    skin_name = args[1].strip()

    deleted = await db.delete_track_skin(user_id, skin_name)
    
    if deleted:
        await message.answer(f"🗑️ Скін **{skin_name}** видалено!", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Не знайшов **{skin_name}** у твоєму списку.", parse_mode="Markdown")

@dp.message(Command("prices"))
async def cmd_prices(message: types.Message):
    user_id = message.from_user.id
    tracked_items = await db.get_user_items(user_id)
    
    if not tracked_items:
        await message.answer("📭 Твій список порожній.", parse_mode="Markdown")
        return

    latest_prices_rows = await db.get_latest_price()
    market_prices = {row['skin_name']: row['price'] for row in latest_prices_rows}

    response = "📊 **Твій портфель:**\n\n"
    
    total_buy_cost = 0 
    total_market_value = 0  
    total_net_value = 0     

    for item in tracked_items:
        name = item['skin_name']
        buy_price = item['buy_price']
        target_price = item.get('target_price')
        
        market_price = market_prices.get(name)

        if market_price:
            market_price = float(market_price)
            net_price = market_price / 1.15
            
            line = f"🔹 **{name}**\n"
            line += f"   💵 Steam: {market_price} $\n"
            line += f"   🤲 На руки: **{net_price:.2f} $**"

            if buy_price:
                diff = market_price - buy_price
                percent = (diff / buy_price) * 100 if buy_price > 0 else 0
                emoji = "🟢" if diff >= 0 else "🔴"
                sign = "+" if diff >= 0 else ""
                
                line += f" | Купив: {buy_price} $\n   {emoji} PnL: **{sign}{diff:.2f} $ ({sign}{percent:.1f}%)**"
                total_buy_cost += buy_price

            if target_price:
                line += f"\n   🔔 Алерт: **< {target_price} $**"

            total_market_value += market_price
            total_net_value += net_price
            
            response += line + "\n\n"
        else:
            response += f"🔹 **{name}**\n   ⏳ Очікування...\n\n"

    if total_market_value > 0:
        total_diff = total_market_value - total_buy_cost
        total_diff_commision = total_net_value - total_buy_cost
        total_percent = (total_diff / total_buy_cost) * 100 if total_buy_cost > 0 else 0
        total_percent_commision = (total_diff_commision / total_buy_cost) * 100 if total_buy_cost > 0 else 0
        emoji = "🚀" if total_diff >= 0 else "🔻"
        emoji_commision = "🚀" if total_diff_commision >= 0 else "🔻"
        sign = "+" if total_diff >= 0 else ""
        sign_commision = "+" if total_diff_commision >= 0 else ""
        
        response += "-"*25 + "\n"
        response += f"💰 **БАЛАНС:**\n"
        response += f"🏦 Активи (Steam): **{total_market_value:.2f} $**\n"
        response += f"🤲 Якщо продати зараз: **{total_net_value:.2f} $**\n"
        
        if total_buy_cost > 0:
            response += f"\n📊 Інвестовано: {total_buy_cost:.2f} $\n"
            response += f"{emoji} Профіт (Paper): **{sign}{total_diff:.2f} $ ({sign}{total_percent:.1f}%)**\n"
            response += f"{emoji_commision} Профіт після продажу: **{sign_commision}{total_diff_commision:.2f} $ ({sign_commision}{total_percent_commision:.1f}%)**"

    await message.answer(response, parse_mode="Markdown")

@dp.message(Command("find"))
async def cmd_find(message: types.Message):
    skin_name = message.text.replace("/find", "").strip()
    if not skin_name:
        await message.answer("ℹ️ Введіть назву.\nПриклад: `/find AWP | Asiimov`", parse_mode="Markdown")
        return

    status_msg = await message.answer(f"🔍 Шукаю: **{skin_name}**...", parse_mode="Markdown")

    client = SteamClient()
    async with aiohttp.ClientSession() as session:
        _, price = await client.get_price(session, skin_name)

    if price:
        await status_msg.edit_text(
            f"✅ **{skin_name}**\n💰 Ціна: **{price} $**\n\nДодати: `/add {skin_name}`",
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(f"❌ Не знайдено: `{skin_name}`", parse_mode="Markdown")

@dp.callback_query(F.data == "show_prices")
async def btn_show_prices(callback: CallbackQuery):
    await callback.answer()
    await cmd_prices(callback.message)

@dp.callback_query(F.data == "show_help")
async def btn_show_help(callback: CallbackQuery):
    await callback.answer()
    await cmd_help(callback.message)

@dp.callback_query(F.data == "ask_portfolio")
async def btn_ask_portfolio(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🎒 Інвентар: `/check <посилання>`", parse_mode="Markdown")

async def main():
    await db.connect()
    await db.create_tables()

    asyncio.create_task(start_monitoring(bot))
    print("Background monitoring started")

    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot is online and ready!")

    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually")