import os
import time
import json
import requests
import hmac
import hashlib
import urllib.parse
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Binance API Key & Secret
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Google Sheets 設定
SHEET_ID = os.environ.get("SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # 改成昨天設定的名稱

# Google Sheets 連線
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    creds_json = json.loads(GOOGLE_CREDENTIALS)
except json.JSONDecodeError as e:
    raise ValueError(f"Google Credentials 格式錯誤: {e}")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

# Binance 抓交易紀錄
def get_my_trades(symbol="BTCUSDT", from_id=None):
    base_url = "https://api.binance.com"
    path = "/api/v3/myTrades"
    timestamp = int(time.time() * 1000)

    params = {
        "symbol": symbol,
        "timestamp": timestamp
    }
    if from_id:
        params["fromId"] = from_id

    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{base_url}{path}?{query_string}&signature={signature}"

    headers = {
        "X-MBX-APIKEY": API_KEY
    }

    res = requests.get(url, headers=headers)
    return res.json()

# 測試抓資料
trades = get_my_trades(symbol="BTCUSDT", from_id=46361639504)

# Debug: 先印出 API 回傳內容
print("===== Binance API 回傳 =====")
print(trades)

# 如果回傳是 list 才處理
if isinstance(trades, list) and trades:
    rows = []
    for t in trades:
        trade_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["time"]/1000))
        rows.append([t["symbol"], t["id"], t["price"], t["qty"], t["quoteQty"], trade_time, t["isBuyer"]])

    # 更新到 Google Sheet
    sheet.clear()
    sheet.append_row(["symbol", "id", "price", "qty", "quoteQty", "time", "isBuyer"])
    for row in rows:
        sheet.append_row(row)
    print("✅ Google Sheet 已更新完成")
else:
    print("⚠️ API 回傳不是交易紀錄，請檢查上面輸出")
