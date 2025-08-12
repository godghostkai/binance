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

SYMBOLS = ["BTCUSDT"]  # 你可以加其他幣對

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(SERVICE_ACCOUNT_JSON),
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def binance_signed_request(endpoint, params=None):
    base_url = "https://api.binance.com"
    if params is None:
        params = {}
    timestamp = int(time.time() * 1000)
    params['timestamp'] = timestamp

    query_string = '&'.join([f"{k}={v}" for k,v in params.items()])
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(url, headers=headers)
    data = r.json()
    if isinstance(data, dict) and data.get("code"):
        print(f"Binance API error: {data}")
        return []
    return data if isinstance(data, list) else []

def get_binance_trades(symbol):
    # 不帶 fromId，API 會回傳該交易對全部交易（最多1000筆）
    return binance_signed_request("/api/v3/myTrades", {"symbol": symbol})

# 清空舊資料（注意：會把第一列也清掉）
sheet.clear()

# 寫入表頭
sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])

for symbol in SYMBOLS:
    trades = get_binance_trades(symbol)
    rows = []
    for t in trades:
        trade_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["time"]/1000))
        rows.append([
            t["symbol"], t["id"], t["price"], t["qty"],
            t["quoteQty"], trade_time, t["isBuyer"]
        ])
    if rows:
        sheet.append_rows(rows)

print("✅ Google Sheet 已完整更新全部交易紀錄")
