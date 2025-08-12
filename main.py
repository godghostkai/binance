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

# 先讀取 Google Sheet 現有交易ID，避免重複寫入
existing_ids = set()
all_records = sheet.get_all_records()
for row in all_records:
    try:
        existing_ids.add(int(row["id"]))
    except:
        pass

# 如果 Sheet 是空的，寫入表頭
if len(all_records) == 0:
    sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])

for symbol in SYMBOLS:
    trades = get_binance_trades(symbol)
    if not trades:
        print(f"{symbol} 無任何交易資料或API錯誤")
        continue

    print(f"{symbol} API 回傳第一筆交易 ID: {trades[0]['id']}")

    new_rows = []
    for t in trades:
        tid = int(t["id"])
        if tid not in existing_ids:
            trade_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["time"]/1000))
            new_rows.append([
                t["symbol"], t["id"], t["price"], t["qty"],
                t["quoteQty"], trade_time, t["isBuyer"]
            ])
            existing_ids.add(tid)

    if new_rows:
        sheet.append_rows(new_rows)

print("✅ Google Sheet 已更新完成（不覆蓋舊資料）")
