import os
import time
import hmac
import hashlib
import requests
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

API_KEY = os.environ["BINANCE_API_KEY"]
API_SECRET = os.environ["BINANCE_API_SECRET"]
SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(SERVICE_ACCOUNT_JSON),
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def get_binance_trades(symbol):
    url = "https://api.binance.com/api/v3/myTrades"
    timestamp = int(time.time() * 1000)
    query_string = f"symbol={symbol}&timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(f"{url}?{query_string}&signature={signature}", headers=headers)
    data = r.json()
    return data if isinstance(data, list) else []

sheet.clear()
sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])

for symbol in SYMBOLS:
    trades = get_binance_trades(symbol)
    for t in trades:
        sheet.append_row([
            t["symbol"], t["id"], t["price"], t["qty"],
            t["quoteQty"], t["time"], t["isBuyer"]
        ])

print("✅ Google Sheet 已更新完成")
