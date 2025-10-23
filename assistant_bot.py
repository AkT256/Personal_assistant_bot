import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN
import asyncio



# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Заметки
notes = {}

async def note_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Напиши заметку после команды: /note купить хлеб")
        return
    notes.setdefault(user_id, []).append(text)
    await update.message.reply_text("Заметка добавлена.")

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_notes = notes.get(user_id, [])
    if not user_notes:
        await update.message.reply_text("У тебя пока нет заметок.")
    else:
        msg = "\n".join(f"{i+1}. {n}" for i, n in enumerate(user_notes))
        await update.message.reply_text(f"Твои заметки:\n{msg}")


# Погода
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Укажи город: /weather Москва")
        return
    
    city = " ".join(context.args)
    
    try:
        url = f"https://wttr.in/{city}?format=3"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        await update.message.reply_text(res.text)
    except Exception as e:
        logger.warning("Weather error: %s", e)
        await update.message.reply_text("Не удалось получить погоду.")


# Напоминания
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /remind <минуты> <текст>
    /remind <чч:мм> <текст>
    """
    if len(context.args) < 2:
        await update.message.reply_text(
            "Формат:\n"
            "/remind <минуты> <текст>\n"
            "или\n"
            "/remind <чч:мм> <текст>"
        )
        return

    time_part = context.args[0]
    text = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    now = datetime.now()

    try:
        if ":" in time_part:
            hh, mm = map(int, time_part.split(":"))
            when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)
            delay = (when - now).total_seconds()
            await update.message.reply_text(f"Напоминание установлено на {when.strftime('%H:%M')} — {text}")
        else:
            minutes = int(time_part)
            delay = minutes * 60
            when = now + timedelta(seconds=delay)
            await update.message.reply_text(f"Напоминание через {minutes} мин ({when.strftime('%H:%M')}) — {text}")
    except ValueError:
        await update.message.reply_text("Ошибка: время укажи как '12:30' или число минут.")
        return

    asyncio.create_task(_delayed_reminder(context.bot, chat_id, text, delay))


async def _delayed_reminder(bot, chat_id: int, text: str, delay: float):
    try:
        await asyncio.sleep(delay)
        await bot.send_message(chat_id=chat_id, text=f"Напоминание: {text}")
    except Exception:
        pass




# Планирование задач
tasks = {}

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Формат: /task <ДД.ММ.ГГ> <ЧЧ:ММ> <описание>")
        return

    date_str, time_str = context.args[0], context.args[1]
    text = " ".join(context.args[2:])
    user_id = update.effective_user.id
    tasks.setdefault(user_id, []).append(f"{date_str} {time_str} — {text}")
    await update.message.reply_text(f"Задача добавлена: {date_str} {time_str} — {text}")

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_tasks = tasks.get(user_id, [])
    if not user_tasks:
        await update.message.reply_text("У тебя пока нет задач.")
    else:
        msg = "\n".join(f"{i+1}. {t}" for i, t in enumerate(user_tasks))
        await update.message.reply_text(f"Твои задачи:\n{msg}")

async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks.pop(user_id, None)
    await update.message.reply_text("Все задачи удалены.")


# Новости по интересам
user_feeds = {}

async def set_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Формат: /setfeed <rss-ссылка>")
        return
    link = context.args[0]
    user_id = update.effective_user.id
    user_feeds[user_id] = link
    await update.message.reply_text(f"RSS-лента установлена: {link}")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    url = user_feeds.get(user_id, "https://lenta.ru/rss")
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")
        headlines = []
        for item in items[:5]:
            title = item.find("title").text
            link = item.find("link").text
            headlines.append(f"{title}\n{link}")
        msg = "\n\n".join(headlines)
        await update.message.reply_text(msg)
    except Exception as e:
        logger.warning("News error: %s", e)
        await update.message.reply_text("Не удалось загрузить новости. Проверь ссылку.")


# Общие команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Я твой персональный ассистент."
        "Мои возможности:\n"
        "- Планирование задач (/task, /tasks)\n"
        "- Напоминания (/remind)\n"
        "- Погода (/weather)\n"
        "- Заметки (/note, /notes)\n"
        "- Новости по интересам (/setfeed, /news)\n\n"
        "Введи /help для списка команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Список команд:\n"
        "/start — запуск бота\n"
        "/help — помощь\n"
        "/weather <город> — погода \n"
        "/note <текст> — добавить заметку\n"
        "/notes — показать заметки\n"
        "/remind <минуты> <текст> — напоминание\n"
        "/task <ДД.ММ.ГГ> <ЧЧ:ММ> <текст> — добавить задачу\n"
        "/tasks — показать задачи\n"
        "/clear_tasks — удалить все задачи\n"
        "/setfeed <rss-ссылка> — задать источник новостей\n"
        "/news — показать последние новости"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Ты сказал: {update.message.text}")


# Запуск приложения
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("note", note_add))
    app.add_handler(CommandHandler("notes", show_notes))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("task", add_task))
    app.add_handler(CommandHandler("tasks", show_tasks))
    app.add_handler(CommandHandler("clear_tasks", clear_tasks))
    app.add_handler(CommandHandler("setfeed", set_feed))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
