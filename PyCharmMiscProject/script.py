import logging
import re
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# --- Конфиг ---
TOKEN = "8427995643:AAEPWeLmIERHxOQobvtnhNIvYzClqw7-oSE"
ADMIN_ID = 5643226867
CHAT_ID = -1002465516886
PRICE = 20000

# --- Лог ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Хранилище ---
WAITING_STEP = {}
TEMP_DATA = {}
BOOKINGS = {
    "Кабина - 1": [],
    "Кабина - 2": [],
    "Кабина - 3": [],
    "Голд кабина - 1": [],
    "Голд кабина - 2": []
}

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Кабина - 1", "Кабина - 2", "Кабина - 3"],
        ["Голд кабина - 1", "Голд кабина - 2"]
    ]
    await update.message.reply_text(
        f"Ассалому алайкум, {update.effective_user.first_name}!\n"
        f"Стоимость залога: {PRICE} сум.\nВыберите кабину:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    WAITING_STEP[update.effective_user.id] = "choose_cabin"

# --- Выбор кабины ---
async def choose_cabin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cabin = update.message.text
    if cabin not in BOOKINGS:
        await update.message.reply_text("Выберите кабину из списка.")
        return

    TEMP_DATA[update.effective_user.id] = {"cabin": cabin}
    WAITING_STEP[update.effective_user.id] = "phone"

    booked_times = BOOKINGS[cabin]
    if booked_times:
        busy_list = "\n".join([f"{t[0]} - {t[1]}" for t in booked_times])
        await update.message.reply_text(f"⏰ Занятые слоты для {cabin}:\n{busy_list}")
    else:
        await update.message.reply_text(f"✅ Все время свободно для {cabin}")

    await update.message.reply_text("Введите свой номер телефона в формате +998 XX XXX XX XX или без пробелов")

# --- Проверка телефона ---
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    phone_clean = phone.replace(" ", "")

    if not re.fullmatch(r"\+998\d{9}", phone_clean):
        await update.message.reply_text("❌ Неверный формат. Введите номер в формате: +998 XX XXX XX XX")
        return

    formatted_phone = f"{phone_clean[:4]} {phone_clean[4:6]} {phone_clean[6:9]} {phone_clean[9:11]} {phone_clean[11:]}"
    TEMP_DATA[update.effective_user.id]["phone"] = formatted_phone
    WAITING_STEP[update.effective_user.id] = "time"
    await update.message.reply_text("Введите время аренды (например: 17:00 - 18:00, 17 - 18, или 17 18)")

# --- Проверка времени ---
def time_overlap(start1, end1, start2, end2):
    return not (end1 <= start2 or start1 >= end2)

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_input = update.message.text.strip()

    # Распознаём несколько форматов
    patterns = [
        r"^(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})$",
        r"^(\d{2})\s*-\s*(\d{2})$",
        r"^(\d{2})\s+(\d{2})$"
    ]

    match = None
    for p in patterns:
        match = re.match(p, time_input)
        if match:
            break

    if not match:
        await update.message.reply_text("❌ Неверный формат. Введите время в формате HH:MM - HH:MM, HH - HH или HH HH")
        return

    if len(match.groups()) == 4:
        start = f"{match.group(1)}:{match.group(2)}"
        end = f"{match.group(3)}:{match.group(4)}"
    elif len(match.groups()) == 2:
        start = f"{match.group(1)}:00"
        end = f"{match.group(2)}:00"
    else:
        await update.message.reply_text("❌ Ошибка распознавания времени")
        return

    cabin = TEMP_DATA[update.effective_user.id]["cabin"]
    for booked_start, booked_end in BOOKINGS[cabin]:
        if time_overlap(start, end, booked_start, booked_end):
            busy_list = "\n".join([f"{t[0]} - {t[1]}" for t in BOOKINGS[cabin]])
            await update.message.reply_text(f"❌ Это время занято.\n⏰ Занятые слоты:\n{busy_list}")
            return

    TEMP_DATA[update.effective_user.id]["time"] = (start, end)
    WAITING_STEP[update.effective_user.id] = "screenshot"
    await update.message.reply_text(f"Переведите {PRICE} сум и отправьте скриншот подтверждения. 5614 6816 2063 9082")

# --- Приём скриншота ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if WAITING_STEP.get(update.effective_user.id) != "screenshot":
        await update.message.reply_text("Сначала начните заказ через /start")
        return

    data = TEMP_DATA[update.effective_user.id]
    photo_id = update.message.photo[-1].file_id

    caption = (
        f"📌 Новая заявка!\n"
        f"👤 Пользователь: {update.effective_user.full_name} (@{update.effective_user.username or 'нет'})\n"
        f"🏠 Кабина: {data['cabin']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"⏰ Время: {data['time'][0]} - {data['time'][1]}\n"
        f"💰 Залог: {PRICE} сум"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{update.effective_user.id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{update.effective_user.id}")]
    ])

    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, reply_markup=keyboard)
    await update.message.reply_text("✅ Заявка отправлена администратору. Ожидайте ответа.")

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_caption(caption="⛔ Только администратор может подтверждать.")
        return

    if action == "confirm":
        data = TEMP_DATA[user_id]
        BOOKINGS[data["cabin"]].append(data["time"])

        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=(
                f"✅ Бронь подтверждена!\n"
                f"🏠 Кабина: {data['cabin']}\n"
                f"📱 Телефон: {data['phone']}\n"
                f"⏰ Время: {data['time'][0]} - {data['time'][1]}"
            )
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваша бронь подтверждена!\n🏠 {data['cabin']}\n⏰ {data['time'][0]} - {data['time'][1]}"
        )

        await query.edit_message_caption(caption="✅ Заявка подтверждена.")

    elif action == "reject":
        WAITING_STEP[ADMIN_ID] = f"reject_reason_{user_id}"
        await context.bot.send_message(chat_id=ADMIN_ID, text="Введите причину отклонения:")

# --- Причина отклонения ---
async def reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = WAITING_STEP.get(ADMIN_ID, "")
    if step.startswith("reject_reason_") and update.effective_user.id == ADMIN_ID:
        user_id = int(step.split("_")[2])
        await context.bot.send_message(chat_id=user_id, text=f"❌ Ваша заявка отклонена.\nПричина: {update.message.text}")
        await update.message.reply_text("Причина отправлена пользователю.")
        WAITING_STEP.pop(ADMIN_ID, None)

# --- Роутинг ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = WAITING_STEP.get(update.effective_user.id)
    if step == "choose_cabin":
        await choose_cabin(update, context)
    elif step == "phone":
        await get_phone(update, context)
    elif step == "time":
        await get_time(update, context)
    elif isinstance(step, str) and step.startswith("reject_reason_") and update.effective_user.id == ADMIN_ID:
        await reject_reason(update, context)
    else:
        await update.message.reply_text("Неизвестная команда. Используйте /start.")

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
