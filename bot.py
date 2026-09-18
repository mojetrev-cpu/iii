import os
import time
import uuid
import requests
import telebot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("8938162529:AAF7GIF5nTlqt1B2BvssOQ4Zxcm_UnKv5bk")
GIGACHAT_AUTH_KEY = os.getenv("MDFhMGIzNjgtODg0Mi03NDJkLThlZGYtODgzNmVlYzIxMjIzOjc2YzUyYzliLWFjNDYtNGY2NC1hZjdhLWQ0ZGJhMzQ4M2NiMg==")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

_giga_access_token = None
_giga_token_expires_at = 0


def get_valid_gigachat_token():
    global _giga_access_token, _giga_token_expires_at
    if _giga_access_token and time.time() < _giga_token_expires_at - 60:
        return _giga_access_token

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
    }
    data = {"scope": GIGACHAT_SCOPE}

    response = requests.post(OAUTH_URL, headers=headers, data=data, verify=False)
    response.raise_for_status()
    result = response.json()
    _giga_access_token = result["access_token"]
    _giga_token_expires_at = result["expires_at"] / 1000
    return _giga_access_token


def ask_gigachat(user_message):
    token = get_valid_gigachat_token()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7,
        "max_tokens": 512,
    }
    response = requests.post(CHAT_URL, headers=headers, json=data, verify=False)
    if response.status_code == 401:
        # токен истёк — сбрасываем кэш и пробуем снова
        global _giga_access_token
        _giga_access_token = None
        token = get_valid_gigachat_token()
        headers["Authorization"] = f"Bearer {token}"
        response = requests.post(CHAT_URL, headers=headers, json=data, verify=False)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, f"Привет, {message.from_user.first_name}! Задай мне любой вопрос.")


@bot.message_handler(content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    answer = ask_gigachat(message.text)
    bot.reply_to(message, answer)


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    bot.infinity_polling()
