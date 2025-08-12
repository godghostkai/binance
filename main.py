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

SYMBOLS = ["BTCUSDT"]  # 你只抓BTC/USDT

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(SERVICE_ACCOUNT_JSON),
    ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def get_last_trade_id(symbol):
    try:
        val = sheet.cell(1, 1).value
        if val:
            pairs = val.split(",")
            for p in pairs:
                s, tid = p.split(":")
                if s == symbol and tid != "None":
                    return int(tid)
    except Exception:
        pass
    # 如果沒找到，從7月初起始交易ID開始
    return 46361639504

def save_last_trade_id(trade_ids):
    s = ",".join([f"{k}:{v}" for k,v in trade_ids.items()])
    sheet.update_cell(1, 1, s)

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
    return data if isinstance(data, list) else []

def get_binance_trades(symbol, fromId=None):
    params = {"symbol": symbol}
    if fromId:
        params['fromId'] = fromId
    return binance_signed_request("/api/v3/myTrades", params)

# 讀取 Google Sheet 現有交易ID，避免重複寫入
existing_ids = set()
all_records = sheet.get_all_records()
for row in all_records:
    try:
        existing_ids.add(int(row["id"]))
    except:
        pass

# 如果 Sheet 沒有資料，先寫入表頭（不會覆蓋第一列儲存的最後交易ID）
if len(all_records) == 0:
    sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])

last_trade_ids = {}
new_rows = []
new_last_ids = {}

for symbol in SYMBOLS:
    fromId = get_last_trade_id(symbol)
    trades = get_binance_trades(symbol, fromId)
    if trades:
        for t in trades:
            tid = int(t["id"])
            if tid not in existing_ids:
                new_rows.append([
                    t["symbol"], t["id"], t["price"], t["qty"],
                    t["quoteQty"], t["time"], t["isBuyer"]
                ])
                existing_ids.add(tid)
                if symbol not in new_last_ids or tid > new_last_ids[symbol]:
                    new_last_ids[symbol] = tid
    else:
        new_last_ids[symbol] = fromId

if new_rows:
    sheet.append_rows(new_rows)

save_last_trade_id(new_last_ids)

print("✅ Google Sheet 已從指定起點累積更新完成")
