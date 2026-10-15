import requests
from urllib.parse import quote
BASE = "https://api.upstox.com"

class UpstoxAPIError(RuntimeError):
    pass

class UpstoxClient:
    def __init__(self, token):
        if not token or "PASTE_YOUR" in token:
            raise UpstoxAPIError("Missing UPSTOX_ACCESS_TOKEN. Set it in your local .env file.")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    def get(self, path, params=None):
        try:
            r = self.session.get(BASE + path, params=params, timeout=20)
        except requests.RequestException as e:
            raise UpstoxAPIError(f"Network error at {path}: {e}") from e
        if not r.ok:
            try: body = r.json()
            except ValueError: body = r.text[:800]
            raise UpstoxAPIError(f"{path} HTTP {r.status_code}: {body}")
        try: payload = r.json()
        except ValueError as e: raise UpstoxAPIError(f"{path} returned invalid JSON") from e
        if payload.get("status") == "error": raise UpstoxAPIError(f"{path}: {payload}")
        return payload.get("data", payload)

    def option_contracts(self, key):
        return self.get("/v2/option/contract", {"instrument_key": key})

    def option_chain(self, key, expiry):
        return self.get("/v2/option/chain", {"instrument_key": key, "expiry_date": expiry})

    def candles(self, key, minutes=5):
        return self.get(f"/v3/historical-candle/intraday/{quote(key, safe='')}/minutes/{minutes}")

    def instrument_search(self, query):
        return self.get("/v2/instruments/search", {"query": query, "exchanges": "NSE", "segments": "EQ"})
