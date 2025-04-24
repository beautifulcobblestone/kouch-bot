import telebot
import requests
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

print("✅ Бот запущен и ждёт голосовых сообщений.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 Привет! Я — *Kouch AI*\n"
        "Твоя мини-команда по работе с голосом.\n\n"
        "🎙 Отправь мне голосовое сообщение или аудиофайл — и я расшифрую его в текст.\n"
        "🕒 Обычно занимает меньше 1 минуты.\n\n"
        "⚠️ *Важно*: сервис на старте в тестовом режиме. Всё, что отправляешь — остаётся между нами 🤫"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
    file = bot.download_file(file_info.file_path)

    with open("temp.ogg", "wb") as f:
        f.write(file)

    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        files={"file": ("temp.ogg", open("temp.ogg", "rb"))},
        data={"model": "whisper-1"}
    )

    if response.status_code == 200:
        text = response.json().get("text", "🤷‍ Не удалось расшифровать.")
    else:
        text = f"Ошибка: {response.status_code}"

    bot.reply_to(message, text)

bot.polling()
