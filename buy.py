import pandas_ta as ta
from scipy.signal import argrelextrema
import pickle
import os
import time
import pandas as pd
from goldhand_client import client, bot, CHAT_ID, BOT_TOKEN, open_orders_file
from functions import *




def find_buy_signals(rsi_buy_below = 30 ):
    """Vételi szignálok keresése."""
    symbols = get_top_symbols(50)

    for symbol in symbols:
        print('\n\n')
        print('-----------------------')

        data = get_data(symbol)
        if data is None or data.empty:
            print(f"Nincs elérhető adat a(z) {symbol} számára.")
            continue

        last_rsi = data['rsi'].iloc[-1]
        print(f"Feldolgozás alatt: {symbol}, RSI érték: {last_rsi:.2f}")

        if last_rsi < rsi_buy_below and last_rsi > 0:
            open_orders = read_open_positions()
            open_orders_symbols = [order['symbol'] for order in open_orders]

            if symbol in open_orders_symbols:
                print(f"Már van nyitott pozícióm: {symbol}")
            else:
                try:
                    buy_order = market_buy_asset(symbol, 1000)
                    if buy_order is None:
                        print(f"Nem sikerült vásárolni a(z) {symbol}t.")
                        continue

                    average_price = float(buy_order['cummulativeQuoteQty'])/float(buy_order['executedQty'])


                    open_orders.append({'symbol': symbol, 'status': 'open', 'average_buy_price': average_price, 'buy_order': buy_order, 'sell_order': None})
                    with open(open_orders_file, 'wb') as f:
                        pickle.dump(open_orders, f)
                    print(f"Vásárlás végrehajtva: {symbol}, átlagár: {average_price}, költség: {float(buy_order['cummulativeQuoteQty']):.2f} USDC")
                except Exception as e:
                    print(f"Hiba a vásárlás során ({symbol}): {e}")
        time.sleep(0.1)  # Rate limit elkerülés

find_buy_signals()