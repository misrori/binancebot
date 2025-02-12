from binance.spot import Spot as Client
import pandas as pd
import pandas_ta as ta
import time
import os
from datetime import datetime
import plotly.graph_objects as go
from decimal import Decimal, ROUND_DOWN
from goldhand_client import client, bot, CHAT_ID, BOT_TOKEN, open_orders_file
import pickle





positive_phrases = [
    "🎉 *You just made a profit!* 🚀",
    "🏆 *Another winning trade!* 💰",
    "🌟 *Your trade was a success!* 🔥",
    "🎯 *Bullseye! Easy profit!* 📈",
    "💎 *Another profitable trade!* 💸",
    "🚀 *Moonshot!* 🌕",
    "🎊 *Strategy is paying off!* 🎯",
    "💰 *Cash in!* 💵",
    "🥳 *Profits incoming!* 🎉",
    "🔥 *Another winning move!* 💪"
]

negative_phrases = [
    "😞 *This one didn't go as planned.*",
    "💔 *Keep your head up!*",
    "😢 *Market didn’t work in your favor.*",
    "🥀 *Not your best trade!*",
    "⚠️ *Loss happens, but it's all part of the journey!*",
    "💭 *Stay strong!*",
    "😕 *Stay resilient!*",
    "🛑 *Not your day!*",
    "🌧️ *Loss today, sunshine tomorrow!*",
    "🔄 *Oh it is bad!*"
]


def adjust_to_step_size(amount, step_size):
    return float(Decimal(str(amount)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))

def send_telegram_message(meassage, parse_mode_text="markdown"):
    try:
        bot.send_message(chat_id=CHAT_ID, text=meassage, parse_mode= parse_mode_text)
    except:
        pass

def get_user_balances(asset=None, filter_zero=True):
    info = client.account(omitZeroBalances='true' if filter_zero else 'false')
    df = pd.DataFrame(info['balances'])
    df['free'] = pd.to_numeric(df['free'])
    df['locked'] = pd.to_numeric(df['locked'])
    df['total'] = df['free'] + df['locked']
    df.reset_index(inplace=True, drop=True)
    if asset:
        one_row = df[df['asset'] == asset]
        if len(one_row) == 1:
            return one_row.to_dict('records')[0]
        else:
            raise Exception(f"Asset {asset} not found")
    else:
        return df

def market_buy_asset(symbol: str, usdc_amount: float):
    try:
        ticker = client.ticker_price(symbol=symbol)
        base_asset = symbol.replace("USDC", "")

        before_balance = get_user_balances(filter_zero=False)
        before_usdc = before_balance.loc[before_balance['asset'] == 'USDC', 'free'].values[0]
        before_base_asset = before_balance.loc[before_balance['asset'] == base_asset, 'free'].values[0]
        if before_usdc < usdc_amount:
            print(f"Not enough USDC to buy {base_asset}.")
            return

        print(f"Buying {base_asset} for {usdc_amount} USDC.")
        print(f"USDC balance before buy: ${before_usdc:.2f}, {base_asset} balance before buy: {before_base_asset:.4f} ")

        order = client.new_order(symbol=symbol, side="BUY", type="MARKET", quoteOrderQty = usdc_amount)

        time.sleep(1)
        after_balance = get_user_balances()
        after_usdc = after_balance.loc[after_balance['asset'] == 'USDC', 'free'].values[0]
        after_base_asset = after_balance.loc[after_balance['asset'] == base_asset, 'free'].values[0]

        print(f"Order status: {order['status']}")
        print(f"USDC balance after buy: ${after_usdc:.2f}, {base_asset} balance before buy: {after_base_asset:.4f} ")

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        telegram_message = (
            f"📢 *Új vásárlás!* 📢\n"
            f"📅 *Időpont:* {timestamp}\n"
            f"📌 *Eszköz:* {symbol.replace('USDC', '')}\n"
            f"💰 *Mennyiség:* {float(order['executedQty']):.4f} {base_asset} \n"
            f"💲 *Átlagár:* {(float(order['cummulativeQuoteQty'])/float(order['executedQty']) ):.4f} USD\n"
            f"🔹 *Összköltség:* {float(order['cummulativeQuoteQty']):.2f} USDC"
        )

        # Üzenet küldése Telegramra
        send_telegram_message(telegram_message)
        return order
    except Exception as e:
        print(f"Error placing buy order: {e}")

def market_sell_asset(symbol: str, retry=0):
    try:
        base_asset = symbol.replace("USDC", "")
        
        # 1. Get available balance
        balances = get_user_balances(filter_zero=False)
        free_amount = balances.loc[balances['asset'] == base_asset, 'free'].values[0] if base_asset in balances['asset'].values else 0

        # 2. Get trading rules (lot size)
        exchange_info = client.exchange_info(symbol)
        for filt in exchange_info['symbols'][0]['filters']:
            if filt["filterType"] == "LOT_SIZE":
                step_size = float(filt["stepSize"])
                min_qty = float(filt["minQty"])

        # 3. max sell amount
        sell_amount = adjust_to_step_size(free_amount, step_size)

        # Ensure it's above minimum order quantity
        if sell_amount >= min_qty:

            before_balance = balances.loc[balances['asset'] == 'USDC', 'free'].values[0]
            print(f"Selling {sell_amount} {base_asset}.")
            
            # 4. Place market sell order
            order = client.new_order(symbol=symbol, side="SELL", type="MARKET", quantity=sell_amount)
            time.sleep(1)

            # try one more time if not filled
            if order['status'] == 'EXPIRED' and retry < 1:
                print("Order expired, retrying once...")
                time.sleep(0.1)
                return market_sell_asset(symbol, retry + 1)
            
            after_balance = get_user_balances(filter_zero = False)
            usdc_balance = after_balance.loc[after_balance['asset'] == 'USDC', 'free'].values[0]
            base_asset_balance = after_balance.loc[after_balance['asset'] == base_asset, 'free'].values[0]

            print(f"Order status: {order['status']}")
            print(f"USDC balance after sell: ${usdc_balance}, {base_asset} balance is now: {base_asset_balance}")

            return order
        else:
            print(f"Sell amount {sell_amount} is below minimum order size {min_qty}.")
            return None

    except Exception as e:
        print(f"Error placing sell order: {e}")
        return None

def set_stop_price(symbol, stop_price):
    try:
        client.cancel_open_orders(symbol)
        print(f"Cancelled all open orders for {symbol}.")
    except Exception as e:
        print(f"No open orders to cancel or error occurred: {e}")

    base_asset = symbol.replace("USDC", "")  # Extract asset name (e.g., "ETH")
    account_info = client.account()
    balances = {balance["asset"]: float(balance["free"]) for balance in account_info["balances"]}
    asset_balance = balances.get(base_asset, 0)

    if asset_balance == 0:
        print(f"No available balance for {base_asset}.")
        return

    exchange_info = client.exchange_info(symbol)
    lot_size_filter = next(f for f in exchange_info["symbols"] if f["symbol"] == symbol)["filters"]
    lot_size_filter = next(f for f in lot_size_filter if f["filterType"] == "LOT_SIZE")
    step_size = float(lot_size_filter["stepSize"])

    sell_amount = round(asset_balance // step_size * step_size, 8)

    try:
        stop_loss_order = client.new_order(
            symbol=symbol,
            side="SELL",
            type="STOP_LOSS_LIMIT",
            quantity=sell_amount,
            stopPrice=stop_price,
            price=stop_price * 0.99  # Binance megkövetel egy price értéket
        )
        print(f"Stop-loss order placed: {stop_loss_order}")
    except Exception as e:
        print(f"Error placing stop-loss order: {e}")

def get_portfolio_value(to_telegram = False, number_of_rows = 10):
    try:
        account_info = client.account()
        balances = account_info["balances"]
    except Exception as e:
        print(f"Failed to fetch account balances: {e}")
        return "Error retrieving portfolio."

    assets = []
    total_usd_value = 0

    for balance in balances:
        asset = balance["asset"]
        free = float(balance["free"])
        locked = float(balance["locked"])
        total = free + locked

        if total > 0:
            assets.append({"asset": asset, "free": free, "locked": locked, "total": total, "usd_value": 0})
    assets=assets[:number_of_rows]
    for asset in assets:
        if asset["asset"] in ["USDT", "USDC"]:
            price = 1
        else:
            symbol = asset["asset"] + "USDT"
            try:
                price = float(client.ticker_price(symbol=symbol)["price"])
            except Exception as e:
                price = 0

        asset["usd_value"] = asset["total"] * price
        total_usd_value += asset["usd_value"]

    assets = [asset for asset in assets if asset["usd_value"] > 3]
    data = pd.DataFrame(assets)
    if to_telegram:
        send_telegram_message(  f"Portfólió riport:\n<pre>{data}</pre>" , parse_mode_text='html' )

    return data

def determine_interval(start_time, end_time):
    """
    Meghatározza a megfelelő gyertyaidőszakot úgy, hogy az adatpontok száma ne haladja meg az 1000-et.
    """
    duration_seconds = end_time - start_time  # Az időtartam másodpercben
    intervals = [("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600), ("4h", 14400), ("1d", 86400)]
    
    for interval, seconds_per_candle in intervals:
        num_candles = duration_seconds // seconds_per_candle
        if num_candles <= 1000:
            return interval  # Ezt az időintervallumot használjuk
    
    return "1d"  # Ha nagyon hosszú a trade időtartama, napi gyertyákat használunk



def send_trade_plot(actual_trade):

    buy_time = actual_trade['buy_order']['transactTime'] // 1000
    sell_time = actual_trade['sell_order']['transactTime'] // 1000

    # Három órával visszamegyünk a vételi időből
    start_time = buy_time - (3 * 60 * 60)

    # Meghatározzuk a megfelelő időintervallumot
    interval = determine_interval(start_time, sell_time)

    # K-line adatok lekérése
    klines = client.klines(
        symbol=actual_trade['symbol'],
        interval=interval,
        startTime=start_time * 1000,
        endTime=sell_time * 1000
    )

    # Adatok átalakítása DataFrame-be
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])

    # Időbélyeg konvertálása
    # Convert timestamps to datetime
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Convert prices to float
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

    # Create OHLC plot
    fig = go.Figure(data=go.Ohlc(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    ))

    # Jelöljük a vételi és eladási pontokat
    fig.add_trace(go.Scatter(
        x=[pd.to_datetime(buy_time, unit='s')],
        y=[actual_trade['average_buy_price']],
        mode='markers',
        name='Vételi Ár',
        marker=dict(color='green', size=10)
    ))

    fig.add_trace(go.Scatter(
        x=[pd.to_datetime(sell_time, unit='s')],
        y=[actual_trade['average_sell_price']],
        mode='markers',
        name='Eladási Ár',
        marker=dict(color='red', size=10)
    ))

    # Grafikon beállítások
    fig.update_layout(
        title=f"{actual_trade['symbol']} Árfolyammozgás ({interval} gyertyák)",
        xaxis_title="Idő",
        yaxis_title="Ár (USDT)",
        template="plotly_white",
        hovermode="x unified"
    )
    fig.update_xaxes(mirror=True, ticks='outside', showline=True, linecolor='black', gridcolor='lightgrey')
    fig.update_yaxes(mirror=True, ticks='outside', showline=True, linecolor='black', gridcolor='lightgrey')
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(showlegend=False, height=600, width=1000)


    fig.write_image("static_plot.png")
    bot.send_photo(-1002368684493, photo=open('static_plot.png', 'rb'))

def read_open_positions(include_closed=False):
    """Olvassa be az aktuális nyitott pozíciókat."""
    if os.path.exists(open_orders_file):
        with open(open_orders_file, 'rb') as f:
            positions = pickle.load(f)
            if include_closed:
                return positions
            return [position for position in positions if position['status'] == 'open']
    return []

def get_top_symbols(num_symbols=50):
    """Lekérdezi a top USDC párokat."""
    tickers = client.exchange_info()
    tickers = [ticker for ticker in tickers['symbols'] if ticker['symbol'].endswith('USDC')]
    top_symbols = [x['symbol'] for x in tickers][:num_symbols]
    print(f"Top {num_symbols} symbols: {top_symbols}")
    return top_symbols

def get_data(symbol, interval='5m', limit=800):
    """Lekérdezi egy adott szimbólum történelmi adatait."""
    try:
        klines = pd.DataFrame(client.klines(symbol, interval, limit=limit))
        df = klines.iloc[:, :6]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df.astype(float)
        df['date'] = pd.to_datetime(df['date'], unit='ms')
        df['ticker'] = symbol
        df['rsi'] = ta.rsi(df['close'], 14)
        df.reset_index(inplace=True, drop=True)
        return df
    except Exception as e:
        print(f"Hiba a {symbol} adatlekérésében: {e}")
        return None
