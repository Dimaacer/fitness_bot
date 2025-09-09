import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import matplotlib.pyplot as plt
import os

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Хранилище данных ---
user_data = {}

# --- Главное меню ---
main_menu = [["📅 Тренировочные дни", "⚖️ Вес"],
             ["📊 Прогресс", "🗑 Сброс данных"]]

days_keyboard = [["Понедельник", "Вторник", "Среда"],
                 ["Четверг", "Пятница", "Суббота", "Воскресенье"],
                 ["🔙 Назад"]]

reset_keyboard = [["❌ Сбросить упражнения"],
                  ["❌ Сбросить вес"],
                  ["🔥 Сбросить всё"],
                  ["📅 Сброс по дням"],
                  ["🔙 Назад"]]

day_menu = [["➕ Добавить упражнение"],
            ["📋 Показать упражнения"],
            ["🔙 Назад"]]

# --- Старт ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"weight": [], "exercises": {}}
    await update.message.reply_text("Привет! Я твой фитнес-бот 🏋️‍♂️", 
                                    reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

# --- Обработка сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Главное меню
    if text == "📅 Тренировочные дни":
        await update.message.reply_text("Выбери день:", 
                                        reply_markup=ReplyKeyboardMarkup(days_keyboard, resize_keyboard=True))

    elif text == "⚖️ Вес":
        await update.message.reply_text("Введи свой вес вручную (например: 72.5)")

    elif text == "📊 Прогресс":
        await progress_graph(update, context)

    elif text == "🗑 Сброс данных":
        await update.message.reply_text("Что хочешь сбросить?", 
                                        reply_markup=ReplyKeyboardMarkup(reset_keyboard, resize_keyboard=True))

    # Сброс
    elif text == "❌ Сбросить упражнения":
        user_data[user_id]["exercises"] = {}
        await update.message.reply_text("✅ Все упражнения и тренировки удалены.")

    elif text == "❌ Сбросить вес":
        user_data[user_id]["weight"] = []
        await update.message.reply_text("✅ Все записи веса удалены.")

    elif text == "🔥 Сбросить всё":
        user_data[user_id] = {"weight": [], "exercises": {}}
        await update.message.reply_text("🔥 Все данные полностью сброшены.")

    elif text == "📅 Сброс по дням":
        context.user_data["reset_day_mode"] = True
        await update.message.reply_text("Выбери день для сброса:", 
                                        reply_markup=ReplyKeyboardMarkup(days_keyboard, resize_keyboard=True))

    elif text in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]:
        if "reset_day_mode" in context.user_data and context.user_data["reset_day_mode"]:
            if text in user_data[user_id]["exercises"]:
                del user_data[user_id]["exercises"][text]
                await update.message.reply_text(f"✅ Данные за {text} удалены.", 
                                                reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
            else:
                await update.message.reply_text(f"⚠️ В {text} ещё нет записей.", 
                                                reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
            context.user_data["reset_day_mode"] = False
        else:
            context.user_data["current_day"] = text
            await update.message.reply_text(f"📅 {text} — выбери действие:", 
                                            reply_markup=ReplyKeyboardMarkup(day_menu, resize_keyboard=True))

    # Меню дня
    elif text == "➕ Добавить упражнение":
        if "current_day" in context.user_data:
            await update.message.reply_text("Введи название упражнения:")
            context.user_data["add_exercise_mode"] = True

    elif "add_exercise_mode" in context.user_data and context.user_data["add_exercise_mode"]:
        context.user_data["exercise_name"] = text
        context.user_data["add_exercise_mode"] = False
        context.user_data["add_sets_mode"] = True

        day = context.user_data["current_day"]
        exercise = context.user_data["exercise_name"]

        # Проверяем, был ли крайний результат
        if day in user_data[user_id]["exercises"] and exercise in user_data[user_id]["exercises"][day]:
            prev = user_data[user_id]["exercises"][day][exercise]
            await update.message.reply_text(
                f"📌 Крайний результат: {prev['sets']}x{prev['reps']} {prev['weight']} кг\n\n"
                "Теперь введи новые данные (пример: 3x10x60)"
            )
        else:
            await update.message.reply_text("Теперь введи данные (пример: 3x10x60)")

    elif "add_sets_mode" in context.user_data and context.user_data["add_sets_mode"]:
        try:
            sets, reps, weight = text.split("x")
            sets, reps, weight = int(sets), int(reps), float(weight)
            day = context.user_data["current_day"]
            exercise = context.user_data["exercise_name"]

            if day not in user_data[user_id]["exercises"]:
                user_data[user_id]["exercises"][day] = {}

            user_data[user_id]["exercises"][day][exercise] = {
                "sets": sets, "reps": reps, "weight": weight
            }

            await update.message.reply_text(
                f"✅ Сохранено: {exercise} — {sets}x{reps} {weight} кг",
                reply_markup=ReplyKeyboardMarkup(day_menu, resize_keyboard=True)
            )
        except:
            await update.message.reply_text("⚠️ Ошибка формата! Введи так: 3x10x60")
        finally:
            context.user_data["add_sets_mode"] = False

    elif text == "📋 Показать упражнения":
        day = context.user_data.get("current_day")
        if day and day in user_data[user_id]["exercises"]:
            msg = f"📅 Упражнения за {day}:\n\n"
            for ex, data in user_data[user_id]["exercises"][day].items():
                msg += f"🏋️ {ex}: {data['sets']}x{data['reps']} {data['weight']} кг\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("⚠️ В этот день ещё нет упражнений.")

    elif text == "🔙 Назад":
        if "current_day" in context.user_data:
            del context.user_data["current_day"]
        await update.message.reply_text("🔙 Главное меню", 
                                        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

    # Если введён вес вручную
    else:
        try:
            weight = float(text.replace(",", "."))
            user_data[user_id]["weight"].append(weight)
            await update.message.reply_text(f"✅ Вес {weight} кг сохранён.")
        except:
            await update.message.reply_text("⚠️ Не понял сообщение. Используй кнопки.")

# --- График прогресса (по весу) ---
async def progress_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_data[user_id]["weight"]:
        await update.message.reply_text("Нет данных для построения графика ⚠️")
        return

    weights = [float(w) for w in user_data[user_id]["weight"]]
    plt.plot(weights, marker="o")
    plt.title("Прогресс веса")
    plt.xlabel("Тренировки")
    plt.ylabel("Вес (кг)")

    file_path = "progress.png"
    plt.savefig(file_path)
    plt.close()

    await update.message.reply_photo(photo=open(file_path, "rb"))
    os.remove(file_path)

# --- Запуск бота ---
def main():
    app = Application.builder().token("8443570362:AAE9cCVoxtlKsdmlc0Gbqe1ABKwnQmIO79M").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
