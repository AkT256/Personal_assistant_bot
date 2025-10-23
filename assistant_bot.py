import logging
import requests
from datetime import datetime
from telegram import ForceReply, Update 
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN
import xml.etree.ElementTree as ET

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команды

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"👋 Привет, {user.mention_html()}! Я твой персональный ассистент 🌤️\n\n"
        "Я могу:\n"
        "🗓 Планировать задачи\n"
        "🌦 Показывать погоду\n"
        "📰 Присылать новости\n"
        "📝 Делать заметки\n\n"
        "Введи /help, чтобы узнать больше."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Список команд:\n"
        "/start — запуск бота\n"
        "/help — помощь\n"
        "/weather <город> — погода в городе\n"
        "/note <текст> — создать заметку\n"
        "/notes — показать заметки\n"
        "/time — текущее время\n"
        "/news — последние новости"
    )

# Погода
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("🌆 Укажи город: /weather Москва")
        return
    city = " ".join(context.args)
    api_key = "https://wttr.in/{}?format=3".format(city)
    try:
        res = requests.get(api_key)
        await update.message.reply_text(f"☀️ {res.text}")
    except Exception:
        await update.message.reply_text("❌ Не удалось получить данные о погоде.")

# Заметки
notes = {}

async def note_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("✍️ Напиши заметку после команды: /note купить хлеб")
        return
    notes.setdefault(user_id, []).append(text)
    await update.message.reply_text("✅ Заметка добавлена!")

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_notes = notes.get(user_id, [])
    if not user_notes:
        await update.message.reply_text("📭 У тебя пока нет заметок.")
    else:
        msg = "\n".join(f"{i+1}. {n}" for i, n in enumerate(user_notes))
        await update.message.reply_text(f"📝 Твои заметки:\n{msg}")

# Время
async def time_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now().strftime("%H:%M:%S, %d.%m.%Y")
    await update.message.reply_text(f"🕓 Текущее время: {now}")

# Новости
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получает последние новости с ria.ru"""
    try:
        url = "https://ria.ru/export/rss2/index.xml"
        response = requests.get(url)
        response.encoding = 'utf-8'

        # Разбираем XML
        root = ET.fromstring(response.text)
        items = root.findall(".//item")

        # Берём первые 5 новостей
        headlines = []
        for item in items[:5]:
            title = item.find("title").text
            link = item.find("link").text
            headlines.append(f"📰 {title}\n🔗 {link}")

        msg = "\n\n".join(headlines)
        await update.message.reply_text(msg)

    except Exception as e:
        print(e)
        await update.message.reply_text("⚠️ Новости временно недоступны. Попробуй позже.")

# Эхо (общение)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Ты сказал: {update.message.text}")

# Основная функция
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("note", note_add))
    app.add_handler(CommandHandler("notes", show_notes))
    app.add_handler(CommandHandler("time", time_now))
    app.add_handler(CommandHandler("news", news))

    # Эхо-сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
