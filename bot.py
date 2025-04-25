import telebot
import requests
import os
from dotenv import load_dotenv

# Загружаем переменные среды
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка наличия токенов
if not TELEGRAM_TOKEN:
    print("CRITICAL: TELEGRAM_TOKEN not found!")
    exit(1) # Завершаем работу, если нет токена Telegram

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found! Transcription will fail.")
    # Можно решить, завершать ли работу или нет, если нет ключа OpenAI

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 Привет! Я — *Kouch AI*\n"
        "Твоя мини-команда по работе с голосом.\n\n"
        "🎙 Отправь мне голосовое сообщение или аудиофайл — и я расшифрую его в текст.\n"
        "🕒 Обычно занимает меньше 1 минуты.\n\n"
        "⚠️ *Важно*: сервис на старте в тестовом режиме. Всё, что отправляешь — остаётся между нами 🤫"
    )
    try:
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending welcome to {message.chat.id}: {e}") # Оставляем лог ошибки

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    file_id = None
    temp_filename = f"temp_{chat_id}_{message.message_id}.ogg"
    text = "Произошла ошибка при обработке аудио." # Сообщение по умолчанию

    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id

        if not file_id:
             bot.reply_to(message, "Не удалось получить файл из сообщения.")
             return

        if not OPENAI_API_KEY:
             bot.reply_to(message, "Ошибка конфигурации: API ключ OpenAI не найден.")
             return

        file_info = bot.get_file(file_id)
        file_content = bot.download_file(file_info.file_path)

        with open(temp_filename, "wb") as f:
            f.write(file_content)

        try:
            with open(temp_filename, "rb") as audio_file:
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    files={"file": (temp_filename, audio_file)},
                    data={"model": "whisper-1"}
                )

            if response.status_code == 200:
                transcription_data = response.json()
                text = transcription_data.get("text", "🤷 Не удалось расшифровать (пустой ответ).")
            else:
                # Логируем детальную ошибку, пользователю даем общее сообщение
                print(f"Whisper API Error {response.status_code}: {response.text}")
                text = f"❌ Ошибка сервиса транскрибации ({response.status_code}). Попробуйте позже."

        except requests.exceptions.RequestException as req_err:
            print(f"Whisper network error: {req_err}")
            text = "❌ Ошибка сети при обращении к сервису транскрибации."
        except Exception as whisper_err:
            print(f"Whisper processing error: {whisper_err}")
            text = "❌ Внутренняя ошибка при обработке запроса к сервису транскрибации."
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    except Exception as e:
        print(f"General handle_audio error: {e}")
        # Не отправляем детальную ошибку пользователю из соображений безопасности
        text = "🤷 Произошла внутренняя ошибка при обработке вашего аудио."

    try:
        bot.reply_to(message, text)
    except Exception as send_err:
        print(f"Error replying to user {chat_id}: {send_err}")

# ----- ЗАПУСК БОТА -----
print("✅ Kouch AI Bot запускает polling...")
try:
    # None_stop=True можно добавить для автоматического перезапуска при некоторых ошибках сети
    # skip_pending=True можно добавить, чтобы пропустить старые сообщения при рестарте
    bot.infinity_polling(timeout=60, long_polling_timeout=30, none_stop=True, skip_pending=True)
except Exception as e:
    print(f"🔴 CRITICAL POLLING ERROR (Bot stopped): {e}")
    exit(1) # Завершаем с ошибкой, если polling упал
