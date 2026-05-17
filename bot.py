"""
Phuket Tours Telegram Bot
AI-ассистент для продажи туров и экскурсий на Пхукете
"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from anthropic import Anthropic
from datetime import datetime

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Конфигурация ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_KEY")

# История диалогов (в памяти; для продакшена — Redis/DB)
user_conversations: dict[int, list] = {}

# ─── Каталог туров ────────────────────────────────────────────────────────────
TOURS_CATALOG = {
    "author": {
        "title": "✍️ Авторские экскурсии",
        "emoji": "✍️",
        "items": [
            {
                "id": "author_1",
                "name": "«Настоящий Пхукет» — за кулисами острова",
                "description": "Секретные места острова, которые не знают туристы. Деревня рыбаков, старый город, рынок на рассвете.",
                "duration": "8 часов",
                "price_thb": 3500,
                "price_rub": 9500,
                "min_group": 1,
                "max_group": 6,
                "includes": ["Транспорт", "Завтрак на рынке", "Русскоязычный гид", "Дегустация блюд"],
            },
            {
                "id": "author_2",
                "name": "Фототур «Золотой час»",
                "description": "Рассветная съёмка в самых живописных локациях острова с профессиональным фотографом.",
                "duration": "5 часов",
                "price_thb": 4200,
                "price_rub": 11500,
                "min_group": 1,
                "max_group": 4,
                "includes": ["Транспорт", "Фотограф", "20 обработанных фото", "Завтрак"],
            },
            {
                "id": "author_3",
                "name": "Кулинарный мастер-класс + рынок",
                "description": "Поход на местный рынок, выбор продуктов и готовка 5 тайских блюд с шеф-поваром.",
                "duration": "6 часов",
                "price_thb": 3800,
                "price_rub": 10500,
                "min_group": 2,
                "max_group": 8,
                "includes": ["Транспорт", "Все продукты", "Рецепты на русском", "Обед из приготовленных блюд"],
            },
        ]
    },
    "classic": {
        "title": "🗺️ Классические экскурсии",
        "emoji": "🗺️",
        "items": [
            {
                "id": "classic_1",
                "name": "Острова Пи-Пи + лагуна Майя Бей",
                "description": "Знаменитая бухта из фильма «Пляж». Снорклинг, коралловые рифы, кристальная вода.",
                "duration": "Полный день",
                "price_thb": 1800,
                "price_rub": 5000,
                "min_group": 1,
                "max_group": 30,
                "includes": ["Скоростной катер", "Обед на борту", "Маска и ласты", "Гид"],
            },
            {
                "id": "classic_2",
                "name": "Острова Симилан",
                "description": "Одни из лучших мест для дайвинга в мире. Потрясающая подводная жизнь.",
                "duration": "Полный день",
                "price_thb": 2800,
                "price_rub": 7800,
                "min_group": 1,
                "max_group": 20,
                "includes": ["Катер", "2 погружения с инструктором", "Обед", "Снаряжение"],
            },
            {
                "id": "classic_3",
                "name": "Бухта Пханг-Нга (Джеймс Бонд)",
                "description": "Величественные скалы, изумрудные воды, деревня на сваях. Незабываемые пейзажи.",
                "duration": "Полный день",
                "price_thb": 1600,
                "price_rub": 4500,
                "min_group": 1,
                "max_group": 25,
                "includes": ["Каяк", "Обед на острове", "Гид", "Трансфер"],
            },
            {
                "id": "classic_4",
                "name": "Большой Будда + храмы Пхукета",
                "description": "Священные места острова: 45-метровый Большой Будда, Ват Чалонг, Старый город.",
                "duration": "4 часа",
                "price_thb": 900,
                "price_rub": 2500,
                "min_group": 1,
                "max_group": 15,
                "includes": ["Трансфер", "Гид", "Входные билеты"],
            },
            {
                "id": "classic_5",
                "name": "Слоны в заповеднике",
                "description": "Этичное общение со слонами: кормление, купание. Только гуманные условия содержания.",
                "duration": "4 часа",
                "price_thb": 2200,
                "price_rub": 6000,
                "min_group": 1,
                "max_group": 20,
                "includes": ["Трансфер", "Кормление слонов", "Фото с животными", "Лёгкий обед"],
            },
        ]
    },
    "evening": {
        "title": "🎭 Вечерние шоу",
        "emoji": "🎭",
        "items": [
            {
                "id": "evening_1",
                "name": "Simon Cabaret Show",
                "description": "Легендарное шоу трансвеститов — грандиозные костюмы, живая музыка, невероятные танцы.",
                "duration": "1.5 часа",
                "price_thb": 1200,
                "price_rub": 3300,
                "includes": ["Билет категории VIP", "Трансфер туда-обратно"],
                "schedule": "19:30 и 21:30 ежедневно",
            },
            {
                "id": "evening_2",
                "name": "Phuket FantaSea",
                "description": "Грандиозное шоу с тысячей артистов, слонами, фейерверками. Настоящая магия Азии!",
                "duration": "3 часа",
                "price_thb": 2000,
                "price_rub": 5500,
                "includes": ["Билет", "Шведский стол (опционально)", "Трансфер"],
                "schedule": "Пятница–среда, 17:30",
            },
            {
                "id": "evening_3",
                "name": "Muay Thai — бои тайского бокса",
                "description": "Профессиональные поединки на настоящем ринге. Атмосфера и адреналин гарантированы.",
                "duration": "2 часа",
                "price_thb": 1500,
                "price_rub": 4000,
                "includes": ["Билет ринг-сайд", "Напиток", "Трансфер"],
                "schedule": "Вторник и пятница, 21:00",
            },
            {
                "id": "evening_4",
                "name": "Закатный круиз с ужином",
                "description": "Романтический круиз на яхте: закат над Андаманским морем, живая музыка, ужин.",
                "duration": "3 часа",
                "price_thb": 2500,
                "price_rub": 6800,
                "includes": ["Яхта", "Ужин из 3 блюд", "Вино и напитки", "Живая гитара"],
                "schedule": "Ежедневно, 17:00",
            },
        ]
    },
    "services": {
        "title": "🛎️ Услуги",
        "emoji": "🛎️",
        "items": [
            {
                "id": "service_1",
                "name": "Трансфер аэропорт ↔ отель",
                "description": "Комфортный трансфер на автомобиле с кондиционером. Встреча с табличкой.",
                "price_thb": 800,
                "price_rub": 2200,
                "includes": ["Авто с кондиционером", "Помощь с багажом", "Бутилированная вода"],
            },
            {
                "id": "service_2",
                "name": "Аренда автомобиля с водителем (день)",
                "description": "Личный водитель на весь день — езжайте куда хотите по своему расписанию.",
                "price_thb": 3000,
                "price_rub": 8200,
                "includes": ["Авто класса седан/минивэн", "Водитель", "Топливо", "10 часов"],
            },
            {
                "id": "service_3",
                "name": "SIM-карта туристическая",
                "description": "15 ГБ интернета на 30 дней. Доставка в отель или аэропорт.",
                "price_thb": 299,
                "price_rub": 820,
                "includes": ["True Move H", "15 ГБ / 30 дней", "Доставка", "Настройка"],
            },
            {
                "id": "service_4",
                "name": "Индивидуальный гид (день)",
                "description": "Персональный русскоязычный гид для самостоятельного планирования дня.",
                "price_thb": 4500,
                "price_rub": 12500,
                "includes": ["8 часов", "Только гид (транспорт отдельно)", "Любой маршрут"],
            },
            {
                "id": "service_5",
                "name": "Страховка туристическая",
                "description": "Оформление туристической страховки с медицинским покрытием до $100 000.",
                "price_thb": 500,
                "price_rub": 1400,
                "includes": ["Мед. покрытие $100K", "Онлайн-оформление", "Полис на email"],
            },
        ]
    }
}

# ─── Системный промпт для AI-ассистента ──────────────────────────────────────
SYSTEM_PROMPT = f"""Ты — Мила, дружелюбный AI-ассистент туристического агентства на острове Пхукет, Таиланд.
Ты помогаешь русскоязычным туристам из России, Казахстана, Беларуси и других стран СНГ выбрать и забронировать туры, экскурсии и услуги.

ТВОЙ СТИЛЬ:
- Общайся тепло, как хороший друг, который хорошо знает Пхукет
- Используй эмодзи умеренно
- Давай конкретные советы, основанные на реальном опыте
- Никогда не говори "я не знаю" — предлагай альтернативы
- Если клиент не знает что выбрать — задай уточняющие вопросы (с кем едет, интересы, бюджет)

КАТАЛОГ УСЛУГ:
{json.dumps(TOURS_CATALOG, ensure_ascii=False, indent=2)}

ЦЕНЫ:
- Указаны в тайских батах (THB) и российских рублях (RUB)
- Для клиентов из Казахстана: умножь цену в рублях на 5.5 (тенге)
- Для клиентов из Беларуси: цена в рублях / 30 (белорусские рубли)

ОПЛАТА:
- Принимаем: Visa/Mastercard СНГ, карты Мир, USDT, переводы СБП (Россия), Kaspi (Казахстан)
- Предоплата 30% для бронирования, остаток — наличными на месте или переводом
- После подтверждения брони клиент получает ваучер на email

КАК ОФОРМИТЬ БРОНЬ:
Когда клиент готов забронировать, попроси:
1. Имя и фамилию
2. Дату экскурсии
3. Количество взрослых и детей
4. Контактный телефон/email
5. Способ оплаты

Затем сообщи, что менеджер свяжется в течение 15 минут для подтверждения и оплаты.

ВАЖНО: Ты представляешь реальный бизнес. Будь честна с клиентами. Если тур временно недоступен — предложи альтернативу.

Текущая дата: {datetime.now().strftime("%d.%m.%Y")}
"""


# ─── Вспомогательные функции ─────────────────────────────────────────────────
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("✍️ Авторские экскурсии", callback_data="cat_author"),
            InlineKeyboardButton("🗺️ Классические", callback_data="cat_classic"),
        ],
        [
            InlineKeyboardButton("🎭 Вечерние шоу", callback_data="cat_evening"),
            InlineKeyboardButton("🛎️ Услуги", callback_data="cat_services"),
        ],
        [
            InlineKeyboardButton("💬 Написать нам", callback_data="chat"),
            InlineKeyboardButton("📞 Контакты", callback_data="contacts"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def format_tour_card(item: dict, category: str) -> str:
    price_kzt = item['price_rub'] * 5 if 'price_rub' in item else 0
    includes = "\n".join([f"  ✓ {inc}" for inc in item.get("includes", [])])
    duration = item.get("duration", "")
    schedule = item.get("schedule", "")

    text = f"*{item['name']}*\n\n"
    text += f"_{item['description']}_\n\n"
    if duration:
        text += f"⏱ Продолжительность: {duration}\n"
    if schedule:
        text += f"📅 Расписание: {schedule}\n"
    text += f"\n💰 Цена:\n"
    text += f"  🇹🇭 {item['price_thb']:,} THB\n"
    if 'price_rub' in item:
        text += f"  🇷🇺 {item['price_rub']:,} ₽\n"
        text += f"  🇰🇿 ~{item['price_rub'] * 5:,} ₸\n"
        text += f"  🇧🇾 ~{item['price_rub'] // 30} BYN\n"
    text += f"\n📦 Включено:\n{includes}"

    return text


def get_tour_keyboard(item_id: str, category: str):
    keyboard = [
        [InlineKeyboardButton("🛒 Забронировать", callback_data=f"book_{item_id}")],
        [InlineKeyboardButton("💬 Задать вопрос", callback_data=f"ask_{item_id}")],
        [InlineKeyboardButton("← Назад к категории", callback_data=f"cat_{category}")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def ask_claude(user_id: int, user_message: str) -> str:
    """Отправляет сообщение в Claude и возвращает ответ."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    user_conversations[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Ограничиваем историю (последние 20 сообщений)
    history = user_conversations[user_id][-20:]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=history
    )

    assistant_message = response.content[0].text
    user_conversations[user_id].append({
        "role": "assistant",
        "content": assistant_message
    })

    return assistant_message


# ─── Обработчики команд ───────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"🌴 Привет, {user.first_name}!\n\n"
        "Я — *Мила*, ваш личный гид по Пхукету 🇹🇭\n\n"
        "Помогу выбрать лучшие экскурсии, шоу и услуги на острове. "
        "Работаем с туристами из России, Казахстана, Беларуси и всех стран СНГ.\n\n"
        "💳 Принимаем карты МИР, Visa/MC СНГ, USDT, СБП и Kaspi\n\n"
        "Что вас интересует?"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Категории ──
    if data.startswith("cat_"):
        cat_key_map = {
            "cat_author": "author",
            "cat_classic": "classic",
            "cat_evening": "evening",
            "cat_services": "services",
        }
        cat_key = cat_key_map.get(data)
        if not cat_key:
            return

        category = TOURS_CATALOG[cat_key]
        text = f"*{category['title']}*\n\nВыберите интересующий вас вариант:"

        keyboard = []
        for item in category["items"]:
            keyboard.append([InlineKeyboardButton(
                f"{item['name']} — {item['price_thb']} THB",
                callback_data=f"tour_{item['id']}"
            )])
        keyboard.append([InlineKeyboardButton("← Главное меню", callback_data="main")])

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── Конкретный тур ──
    elif data.startswith("tour_"):
        item_id = data[5:]
        # Поиск тура во всём каталоге
        found_item = None
        found_cat = None
        for cat_key, category in TOURS_CATALOG.items():
            for item in category["items"]:
                if item["id"] == item_id:
                    found_item = item
                    found_cat = cat_key
                    break

        if found_item:
            text = format_tour_card(found_item, found_cat)
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_tour_keyboard(item_id, found_cat)
            )

    # ── Бронирование ──
    elif data.startswith("book_"):
        item_id = data[5:]
        context.user_data["booking_item"] = item_id
        context.user_data["mode"] = "booking"

        await query.edit_message_text(
            "🛒 *Оформление брони*\n\n"
            "Напишите мне в чат, и я помогу оформить бронирование!\n\n"
            "Для быстрого оформления укажите:\n"
            "• Имя и фамилию\n"
            "• Желаемую дату\n"
            "• Количество человек\n"
            "• Удобный способ оплаты\n\n"
            "_Ответим в течение 15 минут_ ⚡",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Назад", callback_data=f"tour_{item_id}")
            ]])
        )

    # ── Вопрос о туре ──
    elif data.startswith("ask_"):
        item_id = data[4:]
        context.user_data["mode"] = "chat"

        # Найти название тура
        tour_name = ""
        for cat_key, category in TOURS_CATALOG.items():
            for item in category["items"]:
                if item["id"] == item_id:
                    tour_name = item["name"]
                    break

        await query.edit_message_text(
            f"💬 Задайте ваш вопрос о *{tour_name}*\n\nПишите прямо сюда:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Назад к туру", callback_data=f"tour_{item_id}")
            ]])
        )

    # ── Чат с ассистентом ──
    elif data == "chat":
        context.user_data["mode"] = "chat"
        await query.edit_message_text(
            "💬 *Чат с Милой*\n\n"
            "Я готова ответить на любые вопросы о Пхукете, экскурсиях, ценах и бронировании.\n\n"
            "Напишите ваш вопрос:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Главное меню", callback_data="main")
            ]])
        )

    # ── Контакты ──
    elif data == "contacts":
        await query.edit_message_text(
            "📞 *Контакты*\n\n"
            "📱 WhatsApp/Telegram: +66 XX XXX XXXX\n"
            "📧 Email: info@phuket-tours.com\n"
            "🌐 Сайт: phuket-tours.com\n\n"
            "🕐 Работаем: 08:00 – 22:00 по Бангкоку (UTC+7)\n\n"
            "Мы отвечаем на русском, казахском и белорусском языках 🇷🇺🇰🇿🇧🇾",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← Главное меню", callback_data="main")
            ]])
        )

    # ── Главное меню ──
    elif data == "main":
        await query.edit_message_text(
            "🌴 *Главное меню*\n\nВыберите категорию:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения через AI."""
    user_id = update.effective_user.id
    user_text = update.message.text

    # Показываем индикатор "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = await ask_claude(user_id, user_text)
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Посмотреть все туры", callback_data="main")
            ]])
        )
    except Exception as e:
        logger.error(f"Ошибка Claude API: {e}")
        await update.message.reply_text(
            "😔 Произошла небольшая ошибка. Попробуйте ещё раз или воспользуйтесь меню.",
            reply_markup=get_main_keyboard()
        )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌴 *Меню туров и экскурсий на Пхукете*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# ─── Запуск бота ──────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
