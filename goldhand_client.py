from binance.spot import Spot as Client
import pandas as pd
from dotenv import load_dotenv
import os
import telebot


load_dotenv()

APIKey = os.environ.get("APIKey")
SecretKey = os.environ.get("SecretKey")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
chat_id = os.environ.get("CHAT_ID")
open_orders_file = 'open_orders.pickle'



client = Client(api_key=APIKey, api_secret=SecretKey, base_url='https://testnet.binance.vision', )
bot = telebot.TeleBot(BOT_TOKEN)
