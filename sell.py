import pandas_ta as ta
from scipy.signal import argrelextrema
import pickle
import os
import time
import pandas as pd
from goldhand_client import client, bot, CHAT_ID, BOT_TOKEN, open_orders_file
from functions import *
import random
from datetime import datetime, timezone


def sell_positions (rsi_sell_above = 80):
    positions = read_open_positions()
    print(len(positions))

    for i in range(len(positions)):
        print('\n\n')
        print('-----------------------')


        current_price = float(client.ticker_price(symbol=positions[i]['symbol'])['price'])
        buy_price = positions[i]['average_buy_price']
        data = get_data(positions[i]['symbol'])
        last_rsi = data['rsi'].iloc[-1]

        print(f"Feldolgozás alatt: {positions[i]['symbol']},  RSI érték: {last_rsi:.2f}, current price {current_price}")

        if  current_price > buy_price:
            current_profit = ((current_price/buy_price) -1 ) *100
            print(f"Current profit: {current_profit:.2f}% ")
        else:
            current_profit =  (1 - (current_price / buy_price)) * -100
            print(f"Current Loss: {current_profit:.2f}% ")


        if last_rsi >rsi_sell_above:
            # sell
            try:
                print(f"Selling {positions[i]['symbol']} rsi is above {rsi_sell_above}")
                positions[i]['status'] = 'closed'
                sell_order_data = market_sell_asset(positions[i]['symbol'])

                sell_price = (float(sell_order_data['cummulativeQuoteQty'])/float(sell_order_data['executedQty']) )

                profit_loss_usd = (float(sell_order_data['cummulativeQuoteQty']) - float(positions[i]['buy_order']['cummulativeQuoteQty']))

                if  profit_loss_usd > 0:
                    result_of_trade = ((sell_price/buy_price) -1 ) *100
                else:
                    result_of_trade =  (1 - (sell_price / buy_price)) * 100


                positions[i]['average_sell_price'] = sell_price
                positions[i]['sell_order'] = sell_order_data

                print(f"Result of trade: {result_of_trade:.2f}%, {profit_loss_usd} USD ")

                # Format Telegram message
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # trade time
                # Beolvassuk az időbélyegeket milliszekundumban
                buy_time_ms = positions[i]['buy_order']['transactTime']
                sell_time_ms = positions[i]['sell_order']['transactTime']

                # Átalakítjuk másodpercekké
                buy_time = datetime.fromtimestamp(buy_time_ms / 1000, tz=timezone.utc)
                sell_time = datetime.fromtimestamp(sell_time_ms / 1000, tz=timezone.utc)


                # Kiszámoljuk az eltelt időt
                time_difference = sell_time - buy_time
                hours_difference = time_difference.total_seconds() / 3600


                if sell_price > buy_price:
                    telegram_message = (
                        f"{random.choice(positive_phrases)}\n"
                        f"📢 *You won ${profit_loss_usd:.2f} * 📢\n"
                        f"📅 *Trade time:* {hours_difference:.2f} hours\n"
                        f"📌 *Sold Asset:* {positions[i]['symbol']}\n"
                        f"💰 *Amount Sold:* {float(sell_order_data['executedQty']):.6f}\n"
                        f"💲 *Buy Price:* {buy_price:.4f} USDC\n"
                        f"💲 *Sell Price:* {sell_price:.4f} USDC\n"
                        f"🔹 *Profit %:* {result_of_trade:.2f}%\n"
                        f"💵 *Profit in USD:* {profit_loss_usd:.2f} USDC"
                    )

                else:
                    telegram_message = (
                        f"{random.choice(negative_phrases)}\n"
                        f"📢 *You lost ${abs(profit_loss_usd):.2f} * 📢\n"
                        f"📅 *Trade time:* {hours_difference:.2f} hours\n"
                        f"📌 *Sold Asset:* {positions[i]['symbol']}\n"
                        f"💰 *Amount Sold:* {float(sell_order_data['executedQty']):.6f}\n"
                        f"💲 *Buy Price:* {buy_price:.4f} USDC\n"
                        f"💲 *Sell Price:* {sell_price:.4f} USDC\n"
                        f"🔹 *Loss %:* {result_of_trade:.2f}%\n"
                        f"💵 *Loss in USD:* {abs(profit_loss_usd):.2f} USDC"
                    )

                # Send Telegram message
                send_telegram_message(telegram_message)
                send_trade_plot(positions[i])

            except Exception as e:
                print(f'Error while selling {positions[i]["symbol"]}')
                print(e)
                pass

            finally:
                with open(open_orders_file, 'wb') as f:
                    pickle.dump(positions, f)


sell_positions()
