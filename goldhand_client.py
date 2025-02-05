from binance.spot import Spot as Client
import pandas as pd
from dotenv import load_dotenv
import os
import telebot


load_dotenv()

API_KEY = os.environ.get("API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
open_orders_file = 'open_orders.pickle'



client = Client(api_key=API_KEY, api_secret=SECRET_KEY, base_url='https://testnet.binance.vision', )
bot = telebot.TeleBot(BOT_TOKEN)
