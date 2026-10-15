# Upstox Options Scanner V2.1

Updated to explicitly scan NIFTY, BANKNIFTY, SENSEX and configured stock option underlyings. It calls Upstox Option Contracts to discover expiry and Put/Call Option Chain for CE/PE quotes, OI, volume, bid/ask and Greeks. API errors include HTTP status and response body.

## macOS setup
1. Unzip this folder and open Terminal in it.
2. `python3 -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. `cp .env.example .env`
6. Edit `.env` locally and set `UPSTOX_ACCESS_TOKEN`.
7. `python scanner.py`

This is PAPER/signals-only. It never places orders. Entry is an ask-price reference; SL and targets are illustrative percentages, not guaranteed fills or validated trading advice. Never share your token in chat or commit `.env`.
