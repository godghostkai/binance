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

def get_last_trade_id(symbol):
    # 嘗試從 Sheet 第一列第一欄讀取最後交易 ID，格式是 symbol:lastTradeId
    # 範例： BTCUSDT:12345678
    try:
        val = sheet.cell(1, 1).value
        if val:
            pairs = val.split(",")
            for p in pairs:
                s, tid = p.split(":")
                if s == symbol:
                    return int(tid)
    except Exception:
        pass
    return None

def save_last_trade_id(trade_ids):
    # trade_ids 是 dict {symbol: lastTradeId}
    # 會存成 symbol:lastTradeId,symbol:lastTradeId 字串放第一列第一欄
    s = ",".join([f"{k}:{v}" for k,v in trade_ids.items()])
    sheet.update_cell(1, 1, s)

def get_binance_trades(symbol, fromId=None):
    url = "https://api.binance.com/api/v3/myTrades"
    timestamp = int(time.time() * 1000)
    qs = f"symbol={symbol}&timestamp={timestamp}"
    if fromId:
        qs += f"&fromId={fromId}"
    signature = hmac.new(API_SECRET.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(f"{url}?{qs}&signature={signature}", headers=headers)
    data = r.json()
    return data if isinstance(data, list) else []

# 先讀出目前最後的交易 ID
last_trade_ids = {}
for s in SYMBOLS:
    last_trade_ids[s] = get_last_trade_id(s)

# 讀出現有的交易 ID 集合，避免重複寫入
existing_ids = set()
all_records = sheet.get_all_records()
for row in all_records:
    existing_ids.add(int(row["id"]))

# 如果 Sheet 沒資料，先寫表頭（但要注意第一列是最後交易ID存放）
if len(all_records) == 0:
    sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])

new_last_ids = last_trade_ids.copy()
new_rows = []

for symbol in SYMBOLS:
    fromId = last_trade_ids.get(symbol)
    trades = get_binance_trades(symbol, fromId=fromId)
    if trades:
        for t in trades:
            tid = int(t["id"])
            if tid not in existing_ids:
                new_rows.append([
                    t["symbol"], t["id"], t["price"], t["qty"],
                    t["quoteQty"], t["time"], t["isBuyer"]
                ])
                existing_ids.add(tid)
                # 更新最後交易 ID
                if symbol not in new_last_ids or tid > new_last_ids[symbol]:
                    new_last_ids[symbol] = tid

# 批量新增交易資料
if new_rows:
    sheet.append_rows(new_rows)

# 更新最後交易 ID 存回 Sheet 第一列
save_last_trade_id(new_last_ids)

print("✅ Google Sheet 已累積更新完成")
