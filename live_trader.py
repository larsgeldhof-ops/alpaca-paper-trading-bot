"""
Live paper-trading bot (Alpaca)

Scans a fixed universe of momentum stocks, checks the broad market regime
(SPY vs its 200-day SMA), and places bracket orders with an ATR-based
stop-loss through Alpaca's paper trading API (no real money involved).

Requires a .env file with ALPACA_API_KEY and ALPACA_SECRET_KEY
(see .env.example).

Install:  pip install -r requirements.txt
Run:      python live_trader.py
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# ==========================================
# UNIVERSE & STRATEGY PARAMETERS
# ==========================================
# Multi-asset universe: top momentum stocks
UNIVERSE = ["NVDA", "AAPL", "MSFT", "AMD", "TSLA", "AMZN", "GOOGL", "META"]
FAST_SMA = 50
SLOW_SMA = 60
RSI_THRESH = 40
RISK_PER_TRADE_USD = 10000  # max dollar loss per trade at the stop-loss


def get_market_regime():
    """Checks whether the broad market (S&P 500 / SPY) is bullish."""
    spy = yf.download("SPY", period="1y", interval="1d", progress=False)
    price = spy["Close"]["SPY"] if isinstance(spy.columns, pd.MultiIndex) else spy["Close"]
    sma200 = price.rolling(200).mean().iloc[-1]
    latest_spy = price.iloc[-1]
    return latest_spy > sma200  # True if the market is bullish


def analyze_stock(symbol):
    """Computes SMA, RSI and ATR (volatility) for a given stock."""
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    price = df["Close"][symbol] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
    high = df["High"][symbol] if isinstance(df.columns, pd.MultiIndex) else df["High"]
    low = df["Low"][symbol] if isinstance(df.columns, pd.MultiIndex) else df["Low"]

    data = pd.DataFrame({"Price": price, "High": high, "Low": low}).dropna()

    # Indicators
    data["SMA_Fast"] = data["Price"].rolling(window=FAST_SMA).mean()
    data["SMA_Slow"] = data["Price"].rolling(window=SLOW_SMA).mean()

    # RSI (14)
    delta = data["Price"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # ATR (14) for volatility sizing and stop-loss
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Price"].shift()).abs()
    low_close = (data["Low"] - data["Price"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.rolling(14).mean()

    latest = data.iloc[-1]
    signal = 1 if (latest["SMA_Fast"] > latest["SMA_Slow"]) and (latest["RSI"] > RSI_THRESH) else 0

    return {
        "signal": signal,
        "price": latest["Price"],
        "atr": latest["ATR"],
        "rsi": latest["RSI"]
    }


def run_bot():
    # Write execution timestamp to a log file
    with open("execution_log.txt", "a") as f:
        f.write(f"Bot executed successfully at: {datetime.now()}\n")

    print("\n==========================================")
    print("      QUANT LIVE TRADING ENGINE (ALPACA)   ")
    print("==========================================")

    account = trading_client.get_account()
    buying_power = float(account.buying_power)
    print(f"Portfolio Balance: ${float(account.equity):.2f}")
    print(f"Buying Power:      ${buying_power:.2f}")

    # STEP 1: market regime check (SPY)
    is_bullish_market = get_market_regime()
    print(f"Market Regime (S&P 500 Bullish?): {is_bullish_market}")

    if not is_bullish_market:
        print("--> MARKET REGIME WARNING: S&P 500 is in a downtrend. Skipping new long orders.")

    # Fetch current open positions from Alpaca
    positions = {pos.symbol: float(pos.qty) for pos in trading_client.get_all_positions()}

    # STEP 2: multi-asset scanner
    for symbol in UNIVERSE:
        try:
            metrics = analyze_stock(symbol)
            current_qty = positions.get(symbol, 0)

            print(f"\n[{symbol}] Price: ${metrics['price']:.2f} | RSI: {metrics['rsi']:.1f} | ATR: ${metrics['atr']:.2f} | Current Shares: {current_qty}")

            # ENTRY LOGIC (only if the broader market is also bullish)
            if metrics["signal"] == 1 and current_qty == 0 and is_bullish_market:

                # STEP 3: ATR volatility position sizing
                # Risk is 2x ATR per share
                risk_per_share = 2 * metrics["atr"]
                qty_to_buy = int(RISK_PER_TRADE_USD / risk_per_share)

                # Cap on maximum capital allocated per position ($10,000)
                max_shares_allowed = int(10000 / metrics["price"])
                qty_to_buy = min(qty_to_buy, max_shares_allowed)

                if qty_to_buy > 0 and (qty_to_buy * metrics["price"]) <= buying_power:
                    # STEP 4: stop-loss set at 2x ATR below the entry price
                    stop_loss_price = round(metrics["price"] - risk_per_share, 2)

                    print(f"--> BUY SIGNAL: Ordering {qty_to_buy} shares of {symbol} with Stop-Loss at ${stop_loss_price}...")

                    # Submit order including bracket stop-loss
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=qty_to_buy,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.GTC,
                        stop_loss=StopLossRequest(stop_price=stop_loss_price)
                    )
                    order = trading_client.submit_order(order_data=order_data)
                    print(f"    Order Placed Successfully! Order ID: {order.id}")

            # EXIT LOGIC
            elif metrics["signal"] == 0 and current_qty > 0:
                print(f"--> EXIT SIGNAL: Liquidating position in {symbol}...")
                trading_client.close_position(symbol)
                print(f"    Position in {symbol} closed.")

            else:
                print("--> HOLD: Position aligns with strategy.")

        except Exception as e:
            print(f"Error processing {symbol}: {e}")


if __name__ == "__main__":
    run_bot()
