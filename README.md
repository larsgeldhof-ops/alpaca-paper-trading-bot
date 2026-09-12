# Paper trading bot (Alpaca)

A live-scanning momentum bot that trades on Alpaca's paper trading API
(simulated money, no financial risk) using the same SMA + RSI strategy
from the momentum-trading project, plus a market-regime filter and
ATR-based position sizing and stop-loss.

## What it does

- Checks whether the broad market (S&P 500 / SPY) is above its 200-day
  SMA before allowing new long entries
- Scans a fixed universe of momentum stocks for SMA crossover + RSI signals
- Sizes each position based on ATR (volatility), capped at $10,000 per
  position
- Places bracket orders with an ATR-based stop-loss via Alpaca
- Closes positions when the entry signal disappears
- Logs each run to `execution_log.txt`

## Safety notes

- `paper=True` is hardcoded in both scripts — this trades simulated money
  only, never real funds.
- API credentials are read from a `.env` file, which is git-ignored.
  Copy `.env.example` to `.env` and fill in your own Alpaca keys.
- Never commit a real `.env` file. If credentials are ever accidentally
  exposed, regenerate them immediately in your Alpaca dashboard.

## Tech stack

Python, alpaca-py, yfinance, pandas, numpy, python-dotenv

## Installation

```bash
git clone https://github.com/<your-username>/paper-trading.git
cd paper-trading
pip install -r requirements.txt
cp .env.example .env
# then fill in your own Alpaca paper trading API keys in .env
```

## Usage

```bash
python test_alpaca.py    # verify your credentials and connection
python live_trader.py    # run one scan-and-trade cycle
```

Run `live_trader.py` on a schedule (cron / Task Scheduler) for continuous
operation during market hours.

## Roadmap

- Replace the hardcoded stock universe with a configurable watchlist
- Add Slack/email notifications on order execution
- Track realized P&L over time from the execution log

## License

MIT
