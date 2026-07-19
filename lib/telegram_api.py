import requests
import json
from pathlib import Path


def send_telegram_message(msg):
    current_folder = str(Path(__file__).parent)
    f = open(current_folder + "/telegram_api.json", "r")
    data = json.loads(f.read())
    f.close()
    if not data['telegram-api']['bot_id'] or not data['telegram-api']['bot_key'] or not data['telegram-api']['chat_id']:
        raise Exception("Sorry, The telegram bot API auth file has problem!")
    else:
        telegram_api_url = "https://api.telegram.org/bot{}:{}/sendMessage?chat_id={}&text={}".format(
            data['telegram-api']['bot_id'], data['telegram-api']['bot_key'], data['telegram-api']['chat_id'], msg)
    requests.get(telegram_api_url)
