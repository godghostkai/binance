import time
import requests
import hmac
import hashlib
import os

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_API_SECRET")

BASE_URL = "https://api.binance.com"

def binance_signed_request(path, params):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    timestamp = int(time.time() * 1000)
    query_string += f"&timestamp={timestamp}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    headers = {"X-MBX-APIKEY": API_KEY}
    url = f"{BASE_URL}{path}?{query_string}&signature={signature}"
    r = requests.get(url, headers=headers)
    return r.json()

if __name__ == "__main__":
    symbol = "BTCUSDT"  # 你要查的交易對
    trades = binance_signed_request("/api/v3/myTrades", {
        "symbol": symbol,
        "limit": 500   # 一次最多 500 筆
    })

    for t in trades:
        trade_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["time"]/1000))
        print(f"id={t['id']} | time={trade_time} | price={t['price']} | qty={t['qty']}")
