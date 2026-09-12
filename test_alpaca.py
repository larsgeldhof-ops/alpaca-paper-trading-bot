"""
Alpaca connection test

Quick sanity check that your .env credentials work and that you can
reach your Alpaca paper trading account.

Install:  pip install -r requirements.txt
Run:      python test_alpaca.py
"""

import os

from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

# Load keys from .env file
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# paper=True means you are trading with simulated money
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# Fetch account details
account = trading_client.get_account()
print(f"Account Status: {account.status}")
print(f"Buying Power: ${account.buying_power}")
