import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

import os
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_NAME = "stock.db"

# --- СПИСОК ПОЗИЦИЙ И МИНИМАЛЬНЫЕ ЗНАЧЕНИЯ ---

ITEMS = {
    # Фрукты (кг)
    "Апельсин": 2,
    "Грейпфрут": 2,
    "Лимон": 1,
    "Лайм": 1,
    "Банан": 0.5,
    "Киви": 0.1,
    "Мята": 0.1,
    "Корень имбиря": 0.1,
    "Клубника": 0.5,
    "Вишня": 0.5,

    # Мороженое (кг)
    "Шоколадное мороженое": 0.5,
    "Банановое мороженое": 0.5,
    "Манговое мороженое": 0.5,
    "Клубничное мороженое": 0.5,
    "Ночное мороженое": 0.5,
    "Пиньята мороженое": 0.5,

    # Напитки (литры)
    "Газированная вода": 1.5,
    "Тоник": 1.5,
    "Гранатовый сок": 1.5,
    "Вишневый сок": 1.5,

    # Основное
    "Мед": 1,
    "Зерно": 1,
    "Молоко": 30,
    "Сливки": 5,
    "Безлактоз": 5,
}

YES_NO_ITEMS = [
    "Средство для мытья посуды",
    "Средство для посудомойки",
    "Средство для мытья полов",
    "Удалитель пыли",
    "Средство для чистки плит",
    "Устранитель засоров",
    "Средство для чистки стекол",
    "Губки для посуды",
    "Мыло гостевое",
    "Мыло барное",
    "Мешки большие",
    "Мешки маленькие",
    "Конверты"
]

PACK_ITEMS = [
    "Туалетная бумага",
    "Бумажные полотенца",
    "Салфетки",
    "Перчатки винил",
    "Вода Байкал"
]

ALL_ITEMS = list(ITEMS.keys()) + YES_NO_ITEMS + PACK_ITEMS


# --- СОЗДАНИЕ БАЗЫ ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            name TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.commit()

        for item in ALL_ITEMS:
            await db.execute(
                "INSERT OR IGNORE INTO stock (name, value) VALUES (?, ?)",
                (item, "0")
            )
        await db.commit()


class StockState(StatesGroup):
    waiting_for_value = State()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот учёта остатков.\nКоманда: /count")


@dp.message(Command("count"))
async def start_count(message: types.Message, state: FSMContext):
    await state.update_data(index=0)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT value FROM stock WHERE name=?",
            (ALL_ITEMS[0],)
        )
        previous_value = await cursor.fetchone()

    await message.answer(
        f"{ALL_ITEMS[0]}\n"
        f"Предыдущее значение: {previous_value[0]}\n"
        f"Введите новое значение или /skip"
    )

    await state.set_state(StockState.waiting_for_value)


@dp.message(StockState.waiting_for_value)
async def process_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data["index"]
    item = ALL_ITEMS[index]

    if message.text != "/skip":
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE stock SET value=? WHERE name=?",
                (message.text, item)
            )
            await db.commit()

    index += 1

    if index < len(ALL_ITEMS):
        await state.update_data(index=index)

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(
                "SELECT value FROM stock WHERE name=?",
                (ALL_ITEMS[index],)
            )
            previous_value = await cursor.fetchone()

        await message.answer(
            f"{ALL_ITEMS[index]}\n"
            f"Предыдущее значение: {previous_value[0]}\n"
            f"Введите новое значение или /skip"
        )

    else:
        await state.clear()
        await send_report(message)


async def send_report(message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT name, value FROM stock")
        rows = await cursor.fetchall()

    report = "📦 Отчет:\n\n"
    low_items = []

    for name, value in rows:
        report += f"{name}: {value}\n"

        if name in ITEMS:
            try:
                if float(value) < ITEMS[name]:
                    low_items.append(name)
            except:
                pass

        if name in YES_NO_ITEMS:
            if value.lower() == "мало":
                low_items.append(name)

    if low_items:
        report += "\n⚠️ МАЛО:\n"
        for item in low_items:
            report += f"- {item}\n"
    else:
        report += "\n✅ Всё в норме"

    await message.answer(report)


async def main():
    await init_db()
    await dp.start_polling(bot)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


